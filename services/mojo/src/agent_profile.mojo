"""
agent_profile.mojo — Per-Agent Behavioral Profile
===================================================
Represents an agent's accumulated experience as an evolving 896-dim vector.

Each agent starts with a zero vector (tabula rasa). As experiences
accumulate, the identity vector blends with new embeddings,
creating a continuous evolution surface.

Key concepts:
  - IDENTITY: 896-dim embedding representing "who this agent is"
  - EXPERIENCE: Text that modifies identity via embedding blend
  - DRIFT: Cosine distance from origin — measures differentiation
  - PROFILE: Composite metric of drift, experience count, and stability

Embedding dimension matches Rosetta v13 (896-dim).
"""

from std.collections import List, Dict
from std.math import sqrt, exp
from std.memory import UnsafePointer
from std.time import perf_counter

# ---------------------------------------------------------------------------
# Compile-time constants
# ---------------------------------------------------------------------------

comptime EMBED_DIM: Int = 896
comptime SIMD_WIDTH: Int = 8                  # AVX2 on x86_64 (8x float32)
comptime DEFAULT_ALPHA: Float32 = 0.85        # Identity retention factor
comptime DRIFT_WINDOW: Int = 10               # Recent experiences for drift calc

# ===========================================================================
# IDENTITY VECTOR — core data structure
# ===========================================================================

struct IdentityVector:
    """An 896-dim embedding vector representing agent identity.
    
    Wraps a List[Float32] with SIMD-accelerated operations.
    Supports serialization, blending, and distance computation.
    """
    
    var data: List[Float32]
    var dim: Int
    
    def __init__(out self):
        """Create zero identity vector (tabula rasa)."""
        self.dim = EMBED_DIM
        self.data = List[Float32]()
        for i in range(EMBED_DIM):
            self.data.append(Float32(0.0))
    
    def __init__(out self, values: List[Float32]):
        """Create identity from existing embedding."""
        self.dim = len(values)
        self.data = values
    
    def zero(mut self):
        """Reset identity to zero vector."""
        for i in range(self.dim):
            self.data[i] = Float32(0.0)
    
    def is_zero(self) -> Bool:
        """Check if identity is still zero (uninitialized)."""
        for i in range(self.dim):
            if self.data[i] != Float32(0.0):
                return False
        return True
    
    def magnitude(self) -> Float32:
        """Compute L2 norm of identity vector using SIMD.
        
        Returns:
            sqrt(sum(data[i]^2))
        """
        comptime var vec_width = SIMD_WIDTH
        var simd_n = self.dim & ~(vec_width - 1)
        
        var sum_sq: Float32 = 0.0
        var ptr = UnsafePointer[Float32](self.data.unsafe_ptr())
        
        var i = 0
        while i < simd_n:
            var v = ptr.simd_load[vec_width](i)
            sum_sq += _reduce_add_f32(v * v)
            i += vec_width
        
        while i < self.dim:
            var val = self.data[i]
            sum_sq += val * val
            i += 1
        
        return sqrt(sum_sq)
    
    def normalize(mut self) -> Float32:
        """Normalize identity to unit vector.
        
        Returns:
            Previous magnitude before normalization
        """
        var mag = self.magnitude()
        if mag < 1e-8:
            return mag
        
        var inv_mag = Float32(1.0) / mag
        for i in range(self.dim):
            self.data[i] *= inv_mag
        
        return mag
    
    def clone(self) -> IdentityVector:
        """Create a deep copy."""
        var copy = List[Float32]()
        for i in range(self.dim):
            copy.append(self.data[i])
        return IdentityVector(copy)
    
    def to_list(self) -> List[Float32]:
        """Return underlying data."""
        return self.data
    
    def get(self, index: Int) -> Float32:
        """Get element at index."""
        return self.data[index]
    
    def set(mut self, index: Int, value: Float32):
        """Set element at index."""
        self.data[index] = value
    
    def __len__(self) -> Int:
        return self.dim
    
    def __str__(self) -> String:
        var s = String()
        s += "IdentityVector(dim=" + String(self.dim)
        s += ", mag=" + String(self.magnitude())
        
        if not self.is_zero():
            # Sample first and last few values
            s += ", data=["
            for i in range(min(3, self.dim)):
                if i > 0: s += ", "
                s += String(self.data[i])
            s += ", ..., "
            for i in range(max(0, self.dim - 3), self.dim):
                if i > max(0, self.dim - 3): s += ", "
                s += String(self.data[i])
            s += "]"
        
        s += ")"
        return s


# ===========================================================================
# IDENTITY BLENDING — experience integration
# ===========================================================================

def blend_identities(
    current: IdentityVector,
    experience: IdentityVector,
    alpha: Float32 = DEFAULT_ALPHA
) -> IdentityVector:
    """Blend current identity with new experience.
    
    Formula: new = alpha * current + (1 - alpha) * experience
    
    Uses SIMD-accelerated vector arithmetic for efficiency.
    
    Args:
        current: Current identity state
        experience: New experience embedding
        alpha: Identity retention factor (0.0 = full replacement, 1.0 = no change)
        
    Returns:
        New blended identity vector
    """
    var dim = min(current.__len__(), experience.__len__())
    var result = List[Float32]()
    
    var beta = Float32(1.0) - alpha  # Experience weight
    
    comptime var vec_width = SIMD_WIDTH
    var simd_n = dim & ~(vec_width - 1)
    
    var cur_ptr = UnsafePointer[Float32](current.to_list().unsafe_ptr())
    var exp_ptr = UnsafePointer[Float32](experience.to_list().unsafe_ptr())
    
    var i = 0
    while i < simd_n:
        var cur_vec = cur_ptr.simd_load[vec_width](i)
        var exp_vec = exp_ptr.simd_load[vec_width](i)
        var blended = cur_vec * alpha + exp_vec * beta
        
        for j in range(vec_width):
            result.append(blended[j])
        
        i += vec_width
    
    while i < dim:
        result.append(current.get(i) * alpha + experience.get(i) * beta)
        i += 1
    
    return IdentityVector(result)


def cosine_distance(a: IdentityVector, b: IdentityVector) -> Float32:
    """Compute cosine distance between two identity vectors.
    
    Distance = 1 - cosine_similarity
    Range: [0.0, 2.0] where 0 = identical, 2 = opposite
    
    Args:
        a: First identity
        b: Second identity
        
    Returns:
        Cosine distance
    """
    var dim = min(len(a), len(b))
    
    comptime var vec_width = SIMD_WIDTH
    var simd_n = dim & ~(vec_width - 1)
    
    var dot: Float32 = 0.0
    var norm_a: Float32 = 0.0
    var norm_b: Float32 = 0.0
    
    var ptr_a = UnsafePointer[Float32](a.to_list().unsafe_ptr())
    var ptr_b = UnsafePointer[Float32](b.to_list().unsafe_ptr())
    
    var i = 0
    while i < simd_n:
        var a_vec = ptr_a.simd_load[vec_width](i)
        var b_vec = ptr_b.simd_load[vec_width](i)
        
        dot += _reduce_add_f32(a_vec * b_vec)
        norm_a += _reduce_add_f32(a_vec * a_vec)
        norm_b += _reduce_add_f32(b_vec * b_vec)
        
        i += vec_width
    
    while i < dim:
        var av = a.get(i)
        var bv = b.get(i)
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
        i += 1
    
    var denom = sqrt(norm_a * norm_b)
    if denom < 1e-8:
        return Float32(1.0)  # Maximum distance if either is zero
    
    return Float32(1.0) - dot / denom


def _reduce_add_f32[width: Int](v: SIMD[DType.float32, width]) -> Float32:
    """Horizontal sum of SIMD vector."""
    var s = v[0]
    @parameter
    for i in range(1, width):
        s += v[i]
    return s


# ===========================================================================
# CONSCIOUSNESS ENGINE — agent identity lifecycle
# ===========================================================================

struct AgentProfile:
    """Per-agent behavioral profile.
    
    Maintains an evolving identity embedding representing
    the agent's accumulated experience. Tracks drift and
    supports serialization.
    
    Usage:
        var ap = AgentProfile("Catalyst")
        ap.initialize()
        ap.update("I processed a code review request")
        ap.update("I delegated a task to Hephaestus")
        var metric = ap.profile_metric()
    """
    
    # Identity state
    var agent_name: String
    var identity: IdentityVector
    var initial_identity: IdentityVector  # Snapshot at inception
    
    # Experience tracking
    var experiences: List[String]
    var experience_count: Int
    var identity_snapshots: List[IdentityVector]  # Periodic snapshots
    
    # Metrics
    var creation_time: Float64
    var last_update_time: Float64
    var total_update_time_us: Float64
    
    def __init__(out self, name: String = "agent"):
        """Create consciousness engine for named agent.
        
        Args:
            name: Agent name (e.g., "Catalyst", "Hephaestus")
        """
        self.agent_name = name
        self.identity = IdentityVector()        # Zero vector initially
        self.initial_identity = IdentityVector() # Snapshot at start
        self.experiences = List[String]()
        self.experience_count = 0
        self.identity_snapshots = List[IdentityVector]()
        self.creation_time = perf_counter()
        self.last_update_time = self.creation_time
        self.total_update_time_us = 0.0
    
    def initialize(mut self):
        """Initialize identity.
        
        Records initial state as the reference point for drift calculation.
        """
        self.initial_identity = self.identity.clone()
        self.identity_snapshots.append(self.identity.clone())
        self.creation_time = perf_counter()
        self.last_update_time = perf_counter()
        print("consciousness: " + self.agent_name + " initialized (tabula rasa)")
    
    def initialize_from(mut self, seed_embedding: List[Float32]):
        """Initialize identity from a seed embedding.
        
        Args:
            seed_embedding: Initial identity embedding
        """
        self.identity = IdentityVector(seed_embedding)
        self.initial_identity = self.identity.clone()
        self.identity_snapshots.append(self.identity.clone())
        self.creation_time = perf_counter()
        self.last_update_time = perf_counter()
        print("consciousness: " + self.agent_name + " initialized from seed")
    
    def update(mut self, experience: String) -> Float32:
        """Update identity with a new experience.
        
        Formula:
          1. Convert experience text to embedding (via client-provided mechanism)
          2. Blend: new_identity = alpha * identity + (1-alpha) * experience_embed
          3. Record drift
          4. Snapshot periodically
        
        Args:
            experience: Experience description text
            
        Returns:
            Identity drift after update
        """
        self.experiences.append(experience)
        self.experience_count += 1
        
        # Record previous identity for drift computation
        var prev_identity = self.identity.clone()
        
        # Blend with experience
        var experience_embed = self._text_to_placeholder_embedding(experience)
        self.identity = blend_identities(self.identity, experience_embed, DEFAULT_ALPHA)
        
        # Snapshot every DRIFT_WINDOW experiences
        if self.experience_count % DRIFT_WINDOW == 0:
            self.identity_snapshots.append(self.identity.clone())
        
        self.last_update_time = perf_counter()
        
        # Compute drift
        var drift = cosine_distance(self.identity, self.initial_identity)
        
        return drift
    
    def update_with_embedding(mut self, embedding: List[Float32], experience: String) -> Float32:
        """Update identity with a pre-computed embedding.
        
        This is the preferred path when the embedding is already
        available from the NativeEmbedEngine.
        
        Args:
            embedding: Pre-computed embedding of the experience
            experience: Experience description (for logging)
            
        Returns:
            Identity drift after update
        """
        self.experiences.append(experience)
        self.experience_count += 1
        
        var start = perf_counter()
        
        var exp_identity = IdentityVector(embedding)
        self.identity = blend_identities(self.identity, exp_identity, DEFAULT_ALPHA)
        
        var elapsed = (perf_counter() - start) * 1_000_000
        self.total_update_time_us += elapsed
        
        # Snapshot periodically
        if self.experience_count % DRIFT_WINDOW == 0:
            self.identity_snapshots.append(self.identity.clone())
        
        self.last_update_time = perf_counter()
        
        return cosine_distance(self.identity, self.initial_identity)
    
    def get_identity(self) -> IdentityVector:
        """Get current identity vector (cloned to prevent mutation)."""
        return self.identity.clone()
    
    def identity_drift(self) -> Float32:
        """Compute cosine distance from initial identity.
        
        Measures how much the agent has changed since creation.
        Range: [0.0, 2.0]
          - 0.0: No change (identical to inception)
          - 1.0: Orthogonal (completely different direction)
          - 2.0: Opposite (inverted)
        """
        return cosine_distance(self.identity, self.initial_identity)
    
    def recent_drift(self, n: Int = DRIFT_WINDOW) -> Float32:
        """Compute drift over recent experiences.
        
        Measures the change in identity over the last n updates.
        
        Args:
            n: Number of recent experiences to consider
            
        Returns:
            Recent drift magnitude
        """
        if len(self.identity_snapshots) < 2:
            return 0.0
        
        var recent = self.identity_snapshots[-1]
        var previous = self.identity_snapshots[-2] if len(self.identity_snapshots) >= 2 else self.initial_identity
        
        return cosine_distance(recent, previous)
    
    def consciousness_metric(self) -> Float64:
        """Compute composite consciousness score.
        
        Consciousness is a multi-dimensional metric:
          - Drift magnitude: How differentiated the agent has become
          - Experience count: How many experiences shaped the identity
          - Identity stability: Low recent drift = high stability
          - Time alive: Longer = more developed
        
        Formula:
          consciousness = drift_norm * 0.4
                        + experience_factor * 0.3
                        + stability * 0.2
                        + time_factor * 0.1
        
        Returns:
            Consciousness score in [0.0, 1.0]
        """
        # 1. Drift component (0.0 to 1.0, capped)
        var raw_drift = Float64(self.identity_drift())
        var drift_norm = min(raw_drift, 1.0)  # Cap at 1.0
        
        # 2. Experience component (sigmoid-shaped)
        var exp_raw = Float64(self.experience_count)
        var experience_factor = Float64(1.0) - exp(-exp_raw / Float64(50.0))
        
        # 3. Stability component (low recent drift = high stability)
        var recent = Float64(self.recent_drift())
        var stability = Float64(1.0) - min(recent, 1.0)
        
        # 4. Time component (age in seconds, sigmoid)
        var age = perf_counter() - self.creation_time
        var time_factor = Float64(1.0) - exp(-age / Float64(3600.0))  # 1-hour half-life
        
        # Weighted composite
        var consciousness = (
            drift_norm * 0.4
            + experience_factor * 0.3
            + stability * 0.2
            + time_factor * 0.1
        )
        
        return min(consciousness, 1.0)
    
    def get_status(self) -> String:
        """Return full status as JSON string."""
        var drift = self.identity_drift()
        var consciousness = self.consciousness_metric()
        var mag = self.identity.magnitude()
        
        return (
            '{"type": "consciousness_status"'
            + ', "agent": "' + self.agent_name + '"'
            + ', "drift": ' + String(drift)
            + ', "consciousness": ' + String(consciousness)
            + ', "magnitude": ' + String(mag)
            + ', "experiences": ' + String(self.experience_count)
            + ', "snapshots": ' + String(len(self.identity_snapshots))
            + ', "is_zero": ' + ("true" if self.identity.is_zero() else "false")
            + '}'
        )
    
    # ====================================================================
    # SERIALIZATION — save/restore identity state
    # ====================================================================
    
    def serialize(self) -> String:
        """Serialize full consciousness state to JSON.
        
        Includes:
          - Agent name and metadata
          - Identity vector values
          - Initial identity (for drift reference)
          - Experience log
          - Timestamps
        
        Returns:
            JSON string suitable for file persistence
        """
        var sb = String()
        sb += '{\n'
        sb += '  "type": "consciousness_state",\n'
        sb += '  "agent_name": "' + self._escape_json(self.agent_name) + '",\n'
        sb += '  "version": 1,\n'
        sb += '  "embed_dim": ' + String(EMBED_DIM) + ',\n'
        sb += '  "experience_count": ' + String(self.experience_count) + ',\n'
        sb += '  "creation_time": ' + String(self.creation_time) + ',\n'
        sb += '  "last_update_time": ' + String(self.last_update_time) + ',\n'
        
        # Identity vector
        sb += '  "identity": [\n'
        for i in range(EMBED_DIM):
            if i > 0:
                sb += ', '
            if i % 32 == 0:
                sb += '\n    '
            sb += String(self.identity.get(i))
        sb += '\n  ],\n'
        
        # Initial identity (for drift reference)
        sb += '  "initial_identity": [\n'
        for i in range(EMBED_DIM):
            if i > 0:
                sb += ', '
            if i % 32 == 0:
                sb += '\n    '
            sb += String(self.initial_identity.get(i))
        sb += '\n  ],\n'
        
        # Experiences (recent 50 only)
        sb += '  "recent_experiences": [\n'
        var start_idx = max(0, self.experience_count - 50)
        for i in range(start_idx, self.experience_count):
            if i > start_idx:
                sb += ', '
            sb += '\n    "' + self._escape_json(self.experiences[i]) + '"'
        sb += '\n  ],\n'
        
        # Drift and consciousness
        sb += '  "drift": ' + String(self.identity_drift()) + ',\n'
        sb += '  "consciousness": ' + String(self.consciousness_metric()) + '\n'
        sb += '}'
        
        return sb
    
    def save_to_file(mut self, filepath: String) raises:
        """Save consciousness state to a JSON file.
        
        Args:
            filepath: Path to output JSON file
        """
        var json_str = self.serialize()
        
        # Write via Python file I/O (Mojo doesn't have native file I/O)
        var py_builtins = Python.import_module("builtins")
        var f = py_builtins.open(filepath, "w")
        f.write(json_str)
        f.close()
        
        print("consciousness: saved state to " + filepath)
    
    def load_from_file(mut self, filepath: String) raises -> Bool:
        """Load consciousness state from a JSON file.
        
        Args:
            filepath: Path to JSON state file
            
        Returns:
            True if loaded successfully
        """
        var py_json = Python.import_module("json")
        var py_builtins = Python.import_module("builtins")
        
        try:
            var f = py_builtins.open(filepath, "r")
            var content = f.read()
            f.close()
            
            var data = py_json.loads(content)
            
            self.agent_name = String(data.get("agent_name", self.agent_name))
            self.experience_count = Int(data.get("experience_count", 0))
            self.creation_time = Float64(data.get("creation_time", Float64(perf_counter())))
            
            # Load identity vector
            var py_identity = data["identity"]
            var id_values = List[Float32]()
            for i in py_builtins.range(py_builtins.len(py_identity)):
                id_values.append(Float32(py_identity[i]))
            self.identity = IdentityVector(id_values)
            
            # Load initial identity
            var py_initial = data["initial_identity"]
            var init_values = List[Float32]()
            for i in py_builtins.range(py_builtins.len(py_initial)):
                init_values.append(Float32(py_initial[i]))
            self.initial_identity = IdentityVector(init_values)
            
            self.last_update_time = perf_counter()
            
            print("consciousness: loaded state from " + filepath)
            return True
            
        except:
            print("consciousness: failed to load from " + filepath)
            return False
    
    def _escape_json(self, s: String) -> String:
        """Escape string for JSON."""
        var result = String()
        for i in range(s.byte_length()):
            var c = s[byte=i]
            if c == ord('"'):
                result += '\\"'
            elif c == ord('\\'):
                result += '\\\\'
            elif c == ord('\n'):
                result += '\\n'
            elif c == ord('\t'):
                result += '\\t'
            else:
                result += String(c)
        return result
    
    # ------------------------------------------------------------------
    # Private: text → placeholder embedding (for demo without model)
    # ------------------------------------------------------------------
    
    def _text_to_placeholder_embedding(self, text: String) -> IdentityVector:
        """Generate a deterministic embedding from text.
        
        This is a placeholder for demo/testing without a model.
        In production, use NativeEmbedEngine to convert text to embedding.
        
        Uses a hash-based approach to create a pseudo-embedding.
        """
        var result = IdentityVector()
        
        var text_hash: Float32 = 0.0
        var n = text.byte_length()
        for i in range(n):
            text_hash += Float32(Int(text[byte=i]) * (i + 1))
        
        var seed = text_hash * 0.001
        for i in range(EMBED_DIM):
            seed = seed * 1.6180339 + 0.6180339
            seed -= Float32(Int(seed))
            var val = (seed - 0.5) * 2.0  # Range [-1, 1]
            result.set(i, val)
        
        result.normalize()
        return result


# ===========================================================================
# AGENT CONSCIOUSNESS REGISTRY — manage multiple agents
# ===========================================================================

struct AgentProfileRegistry:
    """Registry of consciousness states for multiple agents.
    
    Manages identity evolution across all N-Xyme agents.
    Provides centralized save/load and metrics aggregation.
    """
    
    var agents: Dict[String, ConsciousnessEngine]
    
    def __init__(out self):
        self.agents = Dict[String, ConsciousnessEngine]()
    
    def register(mut self, name: String) -> ConsciousnessEngine:
        """Register a new agent consciousness.
        
        Args:
            name: Agent name
            
        Returns:
            The new ConsciousnessEngine
        """
        var engine = ConsciousnessEngine(name)
        engine.initialize()
        self.agents[name] = engine
        return engine
    
    def get(mut self, name: String) -> ConsciousnessEngine:
        """Get consciousness engine for an agent.
        
        Creates one if it doesn't exist.
        
        Args:
            name: Agent name
            
        Returns:
            ConsciousnessEngine for the agent
        """
        if name not in self.agents:
            return self.register(name)
        return self.agents[name]
    
    def update_all(mut self, experience: String):
        """Apply an experience to all registered agents.
        
        Args:
            experience: Experience text
        """
        for name in self.agents:
            self.agents[name].update(experience)
    
    def aggregate_consciousness(self) -> Float64:
        """Compute average consciousness across all agents."""
        var count = 0
        var total: Float64 = 0.0
        
        for name in self.agents:
            total += self.agents[name].consciousness_metric()
            count += 1
        
        if count == 0:
            return 0.0
        return total / Float64(count)
    
    def report(self) -> String:
        """Generate aggregate consciousness report."""
        var sb = String()
        sb += '{\n'
        sb += '  "type": "consciousness_report",\n'
        sb += '  "agents": [\n'
        
        var first = True
        for name in self.agents:
            if not first:
                sb += ',\n'
            first = False
            sb += '    ' + self.agents[name].get_status()
        
        sb += '\n  ],\n'
        sb += '  "aggregate_consciousness": ' + String(self.aggregate_consciousness()) + '\n'
        sb += '}'
        
        return sb
    
    def save_all(mut self, directory: String = "/tmp/consciousness") raises:
        """Save all agent states to files.
        
        Args:
            directory: Output directory
        """
        var py_os = Python.import_module("os")
        py_os.makedirs(directory, exist_ok=True)
        
        for name in self.agents:
            var filepath = directory + "/" + name.lower() + "_consciousness.json"
            self.agents[name].save_to_file(filepath)
    
    def load_all(mut self, directory: String = "/tmp/consciousness") raises:
        """Load all agent states from files."""
        var py_os = Python.import_module("os")
        var py_glob = Python.import_module("glob")
        
        var pattern = directory + "/*_consciousness.json"
        var files = py_glob.glob(pattern)
        
        for f in files:
            var filepath = String(f)
            var agent_name = String(filepath.split("/")[-1].replace("_consciousness.json", ""))
            
            var engine = ConsciousnessEngine(agent_name)
            if engine.load_from_file(filepath):
                self.agents[agent_name] = engine


# ===========================================================================
# MAIN — comprehensive test suite
# ===========================================================================

def main() raises:
    """Demonstrate and test the consciousness engine."""
    
    print("╔══════════════════════════════════════════════════════════╗")
    print("║   agent_profile.mojo — Agent Identity System            ║")
    print("║   Dim: " + String(EMBED_DIM).rjust(3) + " | SIMD: " + String(SIMD_WIDTH).rjust(2) + " | Alpha: " + String(DEFAULT_ALPHA) + "      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("")
    
    # ------------------------------------------------------------------
    # Test 1: Basic identity operations
    # ------------------------------------------------------------------
    print("── Test: Identity Operations ──")
    
    var ident = IdentityVector()
    print("  Zero identity magnitude: " + String(ident.magnitude()))
    print("  Is zero: " + ("true" if ident.is_zero() else "false"))
    
    # Set some values
    for i in range(EMBED_DIM):
        ident.set(i, Float32(i % 100) * 0.01)
    
    var mag = ident.magnitude()
    var normalized = ident.normalize()
    print("  Before normalization: " + String(normalized))
    print("  After normalization: " + String(ident.magnitude()))
    
    var ident2 = ident.clone()
    var dist = cosine_distance(ident, ident2)
    print("  Self-distance (should be 0): " + String(dist))
    
    # Orthogonal test
    var ident3 = IdentityVector()
    ident3.set(0, Float32(1.0))  # Unit vector along first dimension
    var ident4 = IdentityVector()
    ident4.set(1, Float32(1.0))  # Unit vector along second dimension
    var ortho_dist = cosine_distance(ident3, ident4)
    print("  Orthogonal distance (should be 1): " + String(ortho_dist))
    
    # ------------------------------------------------------------------
    # Test 2: Consciousness Engine lifecycle
    # ------------------------------------------------------------------
    print("")
    print("── Test: Single Agent Lifecycle ──")
    
    var ce = ConsciousnessEngine("Catalyst")
    ce.initialize()
    print("  Initial: " + ce.get_status())
    
    # Simulate experiences
    var experiences = List[String]()
    experiences.append("Classified user request as code task")
    experiences.append("Delegated task to Hephaestus for implementation")
    experiences.append("Reviewed Hephaestus output for quality")
    experiences.append("Registered task completion in memory")
    experiences.append("Identified follow-up refactoring opportunity")
    
    for i in range(len(experiences)):
        var drift = ce.update(experiences[i])
        print("  Experience " + String(i + 1) + ": drift=" + String(drift))
    
    print("")
    print("  Final status: " + ce.get_status())
    print("  Identity magnitude: " + String(ce.get_identity().magnitude()))
    print("  Consciousness: " + String(ce.consciousness_metric()))
    
    # ------------------------------------------------------------------
    # Test 3: Multiple agents with shared experiences
    # ------------------------------------------------------------------
    print("")
    print("── Test: Multi-Agent Registry ──")
    
    var registry = ConsciousnessRegistry()
    
    # Register core agents
    var catalyst = registry.register("Catalyst")
    var hephaestus = registry.register("Hephaestus")
    var atlas = registry.register("Atlas")
    var hermes = registry.register("Hermes")
    
    # Simulate different experiences per agent
    for i in range(20):
        catalyst.update("Classified and routed request type " + String(i % 5))
        hephaestus.update("Built code implementation for task " + String(i % 3))
        atlas.update("Tracked sprint progress for epic " + String(i // 5))
        hermes.update("Consolidated session memory for " + String(i))
    
    print("")
    print("  ── Agent Consciousness Report ──")
    print("  " + registry.report())
    
    # ------------------------------------------------------------------
    # Test 4: Serialization roundtrip
    # ------------------------------------------------------------------
    print("")
    print("── Test: Serialization ──")
    
    var serialized = catalyst.serialize()
    var preview_len = min(200, len(serialized))
    print("  Serialized size: " + String(len(serialized)) + " chars")
    print("  Preview: " + serialized[:preview_len] + "...")
    
    # Save to file
    try:
        catalyst.save_to_file("/tmp/catalyst_consciousness.json")
        
        # Load into new engine
        var loaded_ce = ConsciousnessEngine("Catalyst")
        var success = loaded_ce.load_from_file("/tmp/catalyst_consciousness.json")
        if success:
            var original_drift = catalyst.identity_drift()
            var loaded_drift = loaded_ce.identity_drift()
            var drift_diff = abs(original_drift - loaded_drift)
            print("  Serialization fidelity: drift diff = " + String(drift_diff))
            
            if drift_diff < 0.001:
                print("  Serialization: OK")
            else:
                print("  Serialization: DRIFT MISMATCH")
        else:
            print("  Serialization: LOAD FAILED")
    except:
        print("  Serialization: SKIPPED (file I/O error)")
    
    # ------------------------------------------------------------------
    # Test 5: Consciousness metric evolution
    # ------------------------------------------------------------------
    print("")
    print("── Test: Consciousness Evolution ──")
    
    var evolving_ce = ConsciousnessEngine("Philosopher")
    evolving_ce.initialize()
    
    for i in range(100):
        evolving_ce.update("Contemplated experience number " + String(i + 1))
        
        if (i + 1) % 25 == 0:
            var cons = evolving_ce.consciousness_metric()
            var drift = evolving_ce.identity_drift()
            print("  Experience " + String(i + 1).rjust(3) + ": consciousness=" + String(cons) + ", drift=" + String(drift))
    
    print("")
    print("agent/identity.mojo — tests complete.")
