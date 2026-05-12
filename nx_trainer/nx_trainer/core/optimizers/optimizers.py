import torch
from torch.optim.optimizer import Optimizer
import math


class Lion(Optimizer):
    def __init__(self, params, lr=1e-4, betas=(0.9, 0.99), weight_decay=0.0):
        defaults = dict(lr=lr, betas=betas, weight_decay=weight_decay)
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue

                grad = p.grad
                if group["weight_decay"] > 0:
                    grad = grad + group["weight_decay"] * p.data

                exp_avg = self.state[p].get("exp_avg")
                if exp_avg is None:
                    exp_avg = torch.zeros_like(p.data)
                    self.state[p]["exp_avg"] = exp_avg

                beta1, beta2 = group["betas"]
                exp_avg.mul_(beta1).add_(grad, alpha=1 - beta1)

                update = torch.sign(exp_avg)
                p.add_(update, alpha=-group["lr"])

        return loss


class Sophia(Optimizer):
    def __init__(self, params, lr=1e-4, betas=(0.9, 0.999), weight_decay=1e-4):
        defaults = dict(lr=lr, betas=betas, weight_decay=weight_decay)
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue

                grad = p.grad
                if group["weight_decay"] > 0:
                    grad = grad + group["weight_decay"] * p.data

                state = self.state[p]
                if len(state) == 0:
                    state["exp_avg"] = torch.zeros_like(p.data)
                    state["exp_avg_sq"] = torch.zeros_like(p.data)
                    state["hessian_diag"] = torch.ones_like(p.data)

                exp_avg, exp_avg_sq, hessian_diag = state["exp_avg"], state["exp_avg_sq"], state["hessian_diag"]

                beta1, beta2 = group["betas"]
                exp_avg.mul_(beta1).add_(grad, alpha=1 - beta1)
                exp_avg_sq.mul_(beta2).addcmul_(grad, grad, alpha=1 - beta2)

                hessian_diag.mul_(0.9).addcmul_(grad * grad, grad, alpha=0.1)

                bias_correction1 = 1 - beta1 ** (state["step"] + 1)
                bias_correction2 = 1 - beta2 ** (state["step"] + 1)
                bias_corrected_exp_avg = exp_avg / bias_correction1
                bias_corrected_exp_avg_sq = exp_avg_sq / bias_correction2

                denom = (torch.sqrt(bias_corrected_exp_avg_sq) / math.sqrt(hessian_diag)) + 1e-8
                step_size = group["lr"] / bias_correction1

                p.addcdiv_(bias_corrected_exp_avg, denom, value=-step_size)

                state["step"] += 1

        return loss


class GaLore(Optimizer):
    def __init__(self, params, lr=1e-4, rank=128, update_proj_gap=200, scale=1.0):
        defaults = dict(lr=lr, rank=rank, update_proj_gap=update_proj_gap, scale=scale)
        super().__init__(params, defaults)
        self.rank = rank
        self.update_proj_gap = update_proj_gap

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue

                grad = p.grad
                state = self.state[p]

                if len(state) == 0:
                    state["U"] = None
                    state["V"] = None
                    state["step"] = 0

                state["step"] += 1

                if state["U"] is None:
                    orig_shape = grad.shape
                    state["orig_shape"] = orig_shape
                    flat_grad = grad.flatten()
                    n, m = flat_grad.shape[0], self.rank
                    if n >= m:
                        state["U"] = torch.randn(m, n, device=grad.device, dtype=grad.dtype) * 0.01
                        state["V"] = torch.zeros(m, device=grad.device, dtype=grad.dtype)
                    else:
                        state["U"] = torch.randn(n, m, device=grad.device, dtype=grad.dtype) * 0.01
                        state["V"] = torch.zeros(n, device=grad.device, dtype=grad.dtype)

                flat_grad = grad.flatten()
                U, V = state["U"], state["V"]

                if U.shape[0] == U.shape[1]:
                    grad_proj = torch.matmul(U, flat_grad)
                else:
                    grad_proj = torch.matmul(U.t(), flat_grad)

                V = 0.99 * V + 0.01 * grad_proj
                state["V"] = V

                if state["step"] % self.update_proj_gap == 0:
                    if U.shape[0] == U.shape[1]:
                        U_new = torch.linalg.solve(
                            V.unsqueeze(-1) * V.unsqueeze(0) + 0.1 * torch.eye(self.rank, device=U.device),
                            torch.matmul(V * torch.matmul(U, flat_grad), V).unsqueeze(-1)
                        ).squeeze()
                    U.data = U_new

                if U.shape[0] == U.shape[1]:
                    unproj = torch.matmul(U.t(), V.unsqueeze(-1)).squeeze()
                else:
                    unproj = torch.matmul(U, V.unsqueeze(-1)).squeeze()

                unproj = unproj.reshape(state["orig_shape"])
                p.add_(group["scale"] * group["lr"] * unproj * 0.0)

        return loss


class AdafactorPlus(Optimizer):
    def __init__(self, params, lr=None, beta1=0.9, beta2=0.999, weight_decay=1e-2, clip_threshold=1.0):
        defaults = dict(lr=lr, beta1=beta1, beta2=beta2, weight_decay=weight_decay, clip_threshold=clip_threshold)
        super().__init__(params, defaults)

    @torch.no_grad()
    def step(self, closure=None):
        loss = None
        if closure is not None:
            with torch.enable_grad():
                loss = closure()

        for group in self.param_groups:
            for p in group["params"]:
                if p.grad is None:
                    continue

                grad = p.grad
                state = self.state[p]

                if len(state) == 0:
                    state["step"] = 0
                    state["exp_avg"] = torch.zeros_like(p.data)
                    state["exp_avg_sq"] = torch.zeros_like(p.data)

                state["step"] += 1

                beta1, beta2 = group["beta1"], group["beta2"]
                exp_avg, exp_avg_sq = state["exp_avg"], state["exp_avg_sq"]

                exp_avg.mul_(beta1).add_(grad, alpha=1 - beta1)

                exp_avg_sq.mul_(beta2).addcmul_(grad, grad, value=1 - beta2)

                denom = (exp_avg_sq.sqrt() / (1 - beta2 ** state["step"])).clamp(min=group["clip_threshold"])
                update = exp_avg / denom

                if group["weight_decay"] > 0:
                    update.add_(p.data, alpha=group["weight_decay"])

                p.add_(update, alpha=-group["lr"])

        return loss


OPTIMIZERS = {
    "adamw": torch.optim.AdamW,
    "lion": Lion,
    "sophia": Sophia,
    "galore": GaLore,
    "adafactor": AdafactorPlus,
}


def create_optimizer(model, optimizer_name: str = "adamw", lr: float = 3e-4, **kwargs):
    optimizer_cls = OPTIMIZERS.get(optimizer_name.lower())
    if optimizer_cls is None:
        raise ValueError(f"Unknown optimizer: {optimizer_name}. Available: {list(OPTIMIZERS.keys())}")

    return optimizer_cls(model.parameters(), lr=lr, **kwargs)