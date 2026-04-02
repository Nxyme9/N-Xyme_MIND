# Building Rules — CODE THAT WORKS

## Rule 1: Search Before Writing
Before writing ANY new code:
1. Search block registry: SELECT * FROM blocks WHERE status='working' AND name LIKE '%keyword%'
2. Search Graphiti: graphiti_search_nodes(query="what I need")
3. Only write from scratch if NOTHING exists

## Rule 2: Verify Before Done
Before claiming "done":
1. Run consciousness trigger: process_event({source:'consciousness', type:'claim_made', data:{claim:'X works'}})
2. If FAIL → fix and re-verify
3. Only claim "done" when consciousness says VERIFIED

## Rule 3: Wire Before Moving On
Before moving to next task:
1. Check: does ANYTHING call this code?
2. If NO → wire it now, not later
3. If I can't prove it fires automatically → it's not done

## Rule 4: Store in Graphiti
After completing ANY task:
1. Store what worked: graphiti_add_episode({text: 'X worked because Y', source: 'learning'})
2. Store what broke: graphiti_add_episode({text: 'X failed because Y', source: 'learning'})
3. Future sessions can find this knowledge
