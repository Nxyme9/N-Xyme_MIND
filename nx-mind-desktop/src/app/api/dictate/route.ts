import { NextResponse } from 'next/server';

const DICTATE_HOST = process.env.DICTATE_HOST || 'localhost';
const DICTATE_PORT = process.env.DICTATE_PORT || '8765';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action, text } = body;

    const baseUrl = `http://${DICTATE_HOST}:${DICTATE_PORT}`;

    if (action === 'start') {
      const response = await fetch(`${baseUrl}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const error = await response.text();
        return NextResponse.json({ error: error }, { status: response.status });
      }

      const data = await response.json();
      return NextResponse.json(data);
    }

    if (action === 'stop') {
      const response = await fetch(`${baseUrl}/stop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const error = await response.text();
        return NextResponse.json({ error: error }, { status: response.status });
      }

      const data = await response.json();
      return NextResponse.json(data);
    }

    if (action === 'status') {
      const response = await fetch(`${baseUrl}/status`, { method: 'GET' });
      const data = await response.json();
      return NextResponse.json(data);
    }

    if (action === 'transcribe') {
      const response = await fetch(`${baseUrl}/transcribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const error = await response.text();
        return NextResponse.json({ error: error }, { status: response.status });
      }

      const data = await response.json();
      return NextResponse.json(data);
    }

    if (action === 'command') {
      return NextResponse.json({ 
        status: 'command_sent',
        command: text 
      });
    }

    return NextResponse.json({ error: 'Unknown action' }, { status: 400 });
  } catch (error) {
    console.error('Dictation API error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to dictation service' },
      { status: 500 }
    );
  }
}

export async function GET() {
  return NextResponse.json({
    service: 'N-Xyme Dictate API',
    version: '1.0.0',
    endpoints: {
      POST: {
        transcribe: 'Send audio for transcription',
        status: 'Get dictation service status',
        command: 'Send voice command'
      }
    }
  });
}