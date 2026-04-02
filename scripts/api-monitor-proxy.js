const http = require('http');
const https = require('https');
const net = require('net');
const { exec } = require('child_process');

const PORT = 9876;

function fire429Trigger(url) {
  console.log(`[429] Rate limited at ${url}`);
  const cmd = `python -c "from trigger_router import TriggerRouter; TriggerRouter('triggers.json').process_event({'source':'rate_limit','type':'api_429','severity':'critical','metrics':{}})"`;
  exec(cmd, (err) => {
    if (err) console.error('[429] Trigger failed:', err.message);
  });
}

function forwardRequest(clientReq, clientRes) {
  let targetUrl;
  try {
    targetUrl = new URL(clientReq.url);
  } catch {
    clientRes.writeHead(400);
    return clientRes.end('Bad Request');
  }

  const protocol = targetUrl.protocol === 'https:' ? https : http;
  const options = {
    hostname: targetUrl.hostname,
    port: targetUrl.port || (targetUrl.protocol === 'https:' ? 443 : 80),
    path: targetUrl.pathname + targetUrl.search,
    method: clientReq.method,
    headers: { ...clientReq.headers, host: targetUrl.hostname }
  };

  const proxyReq = protocol.request(options, (proxyRes) => {
    if (proxyRes.statusCode === 429) fire429Trigger(clientReq.url);
    clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(clientRes);
  });

  proxyReq.on('error', (err) => {
    console.error('[PROXY] Error:', err.message);
    clientRes.writeHead(502);
    clientRes.end('Bad Gateway');
  });

  clientReq.pipe(proxyReq);
}

const server = http.createServer(forwardRequest);

server.on('connect', (req, clientSocket, head) => {
  const [host, port] = req.url.split(':');
  const serverSocket = net.connect(parseInt(port) || 443, host, () => {
    clientSocket.write('HTTP/1.1 200 Connection Established\r\n\r\n');
    if (head.length) serverSocket.write(head);
    serverSocket.pipe(clientSocket);
    clientSocket.pipe(serverSocket);
  });

  serverSocket.on('error', () => clientSocket.end());
  clientSocket.on('error', () => serverSocket.end());
});

server.listen(PORT, () => {
  console.log(`[PROXY] Listening on http://localhost:${PORT}`);
  console.log(`[PROXY] Set HTTPS_PROXY=http://localhost:${PORT}`);
});
