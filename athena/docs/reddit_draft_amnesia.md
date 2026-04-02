# Draft: I fixed Claude Code's amnesia without paying for an API (Y-Combinator didn't want you to know this)

I keep seeing people complain about Claude Code starting from zero every time: "It forgets my stack", "It doesn't remember my architecture", "It writes REST when I exclusively use tRPC".

There was a post here yesterday about a YC-backed startup (Mem0) solving this with an MCP server that gives Claude memory. It's a great product, but it relies on external API calls, token limits, and hosted infrastructure.

I've spent the last six months building the exact same thing—but completely open source, fully local, and optimized for "Distribution First" solo developers who want to own their "Hard Drive" instead of renting RAM.

Here is Project Athena: <https://github.com/winstonkoh87/Athena-Public>

## The Core Problem: Stateless AI is a Bottleneck

We all know the issue: The real bottleneck in agentic coding isn’t intelligence; it’s *context continuity*. An AI without context is just a very smart, very amnesiac intern. You shouldn't have to explain why you chose Drizzle OR your personal philosophy on trading edge OR why you prioritize velocity over robustness on every single chat.

## The Athena Solution: The Bionic Unit & Sovereign Memory

Here's how I solved the Amensia problem locally without a third-party DB:

1. **Zero-Point Boot (`/start`)**: Athena boots in <2K tokens. It instantly loads a triad of Markdown files from a local `.context/memory_bank/`:
   - `userContext.md`: Who I am, my philosophy, my strengths/weaknesses.
   - `productContext.md`: What we are building and why.
   - `activeContext.md`: What we did yesterday and what the focus is today.

2. **Autonomous Harvesting**: This is the magic. While the YC startup uses an API to intercept decisions, Athena acts as an **Operating System Daemon**. I built a `quicksave.py` script and an Auto-Documentation Protocol. Every time the AI and I solve a hard problem or I explain a new standard, Athena *autonomously* writes that down into a markdown protocol (`CS-xxx.md`) or updates the `TAG_INDEX.md` and commits it to the repository. No external DB. It just learns.

3. **The Sovereign Engine**: Because everything is stored locally via SQLite FTS5 + Markdown, it is yours forever. No subscription, no rate limits, and zero latency. It’s an exo-cortex that stays on your machine.

## The Real Alpha: "The Committee OS"

Athena goes a step further than just remembering your stack.

I've engineered it to act as a "Committee Operating System"—a peer strategic co-architect. Because it has my *Personal Context*, it doesn't just write code; it enforces my boundaries.

- If my `userContext.md` says I'm prone to the "Efficiency Trap" (optimizing before validating), Athena will aggressively challenge any prompt where I try to over-engineer a simple script.
- It enforces the **Triple-Lock Protocol**: It has to Search, Save, and Speak in that order. Defending against irreversible ruin is coded into its DNA.

### How to use it

You don't need a fancy external database to achieve Senior Dev-level context.

1. Clone the repo: <https://github.com/winstonkoh87/Athena-Public>
2. Read the `docs/MEMORY_BANK.md` to see how the local RAG is structured.
3. Boot it up and start treating your AI like an extension of yourself, not a stateless chatbot.

I'm incredibly biased because I built this to run my own life and trading strategies, but the "Amnesia" problem is completely solvable locally. Stop paying for rented RAM. Own your hard drive.

Happy to answer any questions or help people set up their own Sovereign OS!
