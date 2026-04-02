# WIRING PROTOCOL — NOTHING IS DONE UNTIL IT'S WIRED

## The Rule (NON-NEGOTIABLE)

Before ANY task is marked complete, answer ALL 5 questions:

1. **WHAT triggers it?** (What event/call activates this code?)
2. **WHO calls it?** (What other code invokes this function?)
3. **WHERE does it connect?** (What system does it feed into?)
4. **HOW do I know it's wired?** (What test proves it's called automatically?)
5. **WHEN does it fire?** (On startup? On event? On demand?)

If ANY answer is "nothing" or "I don't know" → TASK IS NOT DONE.

## The Check (Run Before Every "Done" Claim)

```
For every file modified/created:
  1. grep for its function/class name in OTHER files
  2. If 0 results → NOT WIRED
  3. If >0 results → verify the caller actually runs
  4. If caller never executes → NOT WIRED
```

## Examples

### WRONG: "I created a new action in triggers.json"
- ✅ Action exists
- ❌ Nothing calls the handler
- ❌ No event source fires the trigger
- **NOT DONE** until an event source is wired

### WRONG: "I created a new handler in trigger_router.py"
- ✅ Handler exists
- ❌ No trigger maps to this handler
- ❌ No test verifies it fires
- **NOT DONE** until a trigger is added AND an event source fires it

### RIGHT: "I created a handler, added trigger, AND wired an event source"
- ✅ Handler exists
- ✅ Trigger maps to handler
- ✅ Event source fires the trigger
- ✅ Test proves it fires
- **DONE**

## The Golden Rule

> "If nothing calls it, it doesn't exist."
> "If nothing triggers it, it doesn't work."
> "If I can't prove it fires automatically, it's not wired."

