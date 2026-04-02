/**
 * Ingest old MIND memories into Graphiti
 */

const fs = require('fs');
const path = require('path');
const axios = require('axios');

const GRAPHITI_URL = 'http://localhost:8001/json-rpc';
const ROUTEPLANS_DIR = 'D:\\99_Depricated\\1_N-Xyme_MIND\\.nxm_coder\\memory\\routeplans';

async function ingestRouteplan(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const data = JSON.parse(content);
    
    // Extract meaningful content
    const text = [
      `Routeplan from ${data.ts}`,
      `Mode: ${data.mode}, Cortex: ${data.cortex_mode}`,
      data.planner?.steps?.length > 0 ? `Steps: ${data.planner.steps.map(s => s.action || s.name).join(', ')}` : '',
      data.web_search?.query ? `Web search: ${data.web_search.query}` : '',
      data.summary ? `Summary: ${data.summary}` : ''
    ].filter(Boolean).join('\n');
    
    // Store in Graphiti
    const response = await axios.post(GRAPHITI_URL, {
      jsonrpc: '2.0',
      method: 'graphiti_add_episode',
      params: {
        text,
        metadata: {
          source: 'mind-routeplan',
          file: path.basename(filePath),
          timestamp: data.ts,
          mode: data.mode
        }
      },
      id: Date.now()
    });
    
    return { success: true, file: path.basename(filePath) };
  } catch (error) {
    return { success: false, file: path.basename(filePath), error: error.message };
  }
}

async function main() {
  console.log('=== Ingesting old MIND memories into Graphiti ===');
  
  // Get all routeplan files
  const files = fs.readdirSync(ROUTEPLANS_DIR)
    .filter(f => f.endsWith('.json'))
    .map(f => path.join(ROUTEPLANS_DIR, f));
  
  console.log(`Found ${files.length} routeplan files`);
  
  // Process in batches
  const BATCH_SIZE = 10;
  let ingested = 0;
  let failed = 0;
  
  for (let i = 0; i < files.length; i += BATCH_SIZE) {
    const batch = files.slice(i, i + BATCH_SIZE);
    const results = await Promise.all(batch.map(ingestRouteplan));
    
    for (const result of results) {
      if (result.success) {
        ingested++;
      } else {
        failed++;
        console.error(`Failed: ${result.file} - ${result.error}`);
      }
    }
    
    // Progress
    const progress = Math.min(100, Math.round((i + batch.length) / files.length * 100));
    console.log(`Progress: ${progress}% (${ingested} ingested, ${failed} failed)`);
    
    // Rate limiting - wait between batches
    if (i + BATCH_SIZE < files.length) {
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }
  
  console.log(`\n=== Complete ===`);
  console.log(`Total: ${files.length}, Ingested: ${ingested}, Failed: ${failed}`);
}

main().catch(console.error);
