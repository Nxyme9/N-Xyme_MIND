'use client';

import { useState, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

interface ParsedData {
  rows: Record<string, string>[];
  columns: string[];
  totalRows: number;
  format: 'jsonl' | 'csv';
  filename: string;
}

interface DataUploadProps {
  onComplete?: (data: ParsedData) => void;
}

export function DataUpload({ onComplete }: DataUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [parsedData, setParsedData] = useState<ParsedData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const parseJSONL = (content: string): ParsedData => {
    const lines = content.trim().split('\n').filter(line => line.trim());
    const rows = lines.map((line, idx) => {
      try {
        return JSON.parse(line);
      } catch {
        throw new Error(`Invalid JSON on line ${idx + 1}`);
      }
    });

    const columns = [...new Set(rows.flatMap(row => Object.keys(row)))];

    return {
      rows: rows.slice(0, 5),
      columns,
      totalRows: rows.length,
      format: 'jsonl',
      filename: '',
    };
  };

  const parseCSV = (content: string): ParsedData => {
    const lines = content.trim().split('\n').filter(line => line.trim());
    if (lines.length < 2) {
      throw new Error('CSV must have header row and at least one data row');
    }

    const columns = lines[0].split(',').map(col => col.trim().replace(/^["']|["']$/g, ''));
    const rows = lines.slice(1).map((line, idx) => {
      const values = line.split(',').map(v => v.trim().replace(/^["']|["']$/g, ''));
      const row: Record<string, string> = {};
      columns.forEach((col, i) => {
        row[col] = values[i] || '';
      });
      return row;
    });

    return {
      rows: rows.slice(0, 5),
      columns,
      totalRows: rows.length,
      format: 'csv',
      filename: '',
    };
  };

  const processFile = useCallback(async (file: File) => {
    setIsLoading(true);
    setError(null);

    try {
      const content = await file.text();
      let data: ParsedData;

      if (file.name.endsWith('.jsonl')) {
        data = parseJSONL(content);
      } else if (file.name.endsWith('.csv')) {
        data = parseCSV(content);
      } else {
        throw new Error('Please upload a .jsonl or .csv file');
      }

      data.filename = file.name;
      setParsedData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to parse file');
      setParsedData(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (file) {
      processFile(file);
    }
  }, [processFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      processFile(file);
    }
  }, [processFile]);

  const handleContinue = () => {
    if (parsedData && onComplete) {
      onComplete(parsedData);
    }
  };

  return (
    <div className="space-y-6">
      {!parsedData && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            border-2 border-dashed rounded-lg p-12 text-center cursor-pointer
            transition-all duration-200
            ${isDragging 
              ? 'border-[var(--color-accent)] bg-[var(--color-accent)]/10' 
              : 'border-[var(--color-border)] hover:border-[var(--color-text-secondary)]'
            }
          `}
          style={{ backgroundColor: 'var(--color-bg-secondary)' }}
        >
          <input
            type="file"
            accept=".jsonl,.csv"
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
            disabled={isLoading}
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <div className="space-y-4">
              <div 
                className="w-16 h-16 mx-auto rounded-full flex items-center justify-center"
                style={{ backgroundColor: 'var(--color-bg-tertiary)' }}
              >
                <svg 
                  className="w-8 h-8" 
                  style={{ color: 'var(--color-text-secondary)' }}
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth={2} 
                    d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" 
                  />
                </svg>
              </div>
              <div>
                <p 
                  className="text-lg font-medium"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  {isLoading ? 'Processing...' : 'Drop your training data here'}
                </p>
                <p 
                  className="mt-1"
                  style={{ color: 'var(--color-text-secondary)' }}
                >
                  or click to browse • Supports .jsonl and .csv
                </p>
              </div>
            </div>
          </label>
        </div>
      )}

      {error && (
        <div 
          className="p-4 rounded-lg border"
          style={{ 
            backgroundColor: 'var(--color-danger)/10', 
            borderColor: 'var(--color-danger)',
          }}
        >
          <p style={{ color: 'var(--color-danger)' }}>{error}</p>
        </div>
      )}

      {/* Data Preview */}
      {parsedData && (
        <Card>
          <div className="p-6 space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
              <div>
                <h3 
                  className="text-lg font-semibold"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  {parsedData.filename}
                </h3>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                  {parsedData.totalRows.toLocaleString()} rows • {parsedData.format.toUpperCase()}
                </p>
              </div>
              <Button
                variant="secondary"
                onClick={() => setParsedData(null)}
              >
                Remove
              </Button>
            </div>

            {/* Preview Table */}
            <div 
              className="overflow-x-auto rounded-lg border"
              style={{ borderColor: 'var(--color-border)' }}
            >
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                    {parsedData.columns.map((col) => (
                      <th
                        key={col}
                        className="px-4 py-2 text-left font-medium"
                        style={{ color: 'var(--color-text-primary)' }}
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {parsedData.rows.map((row, idx) => (
                    <tr
                      key={idx}
                      className="border-t"
                      style={{ 
                        borderColor: 'var(--color-border)',
                        backgroundColor: idx % 2 === 0 ? 'transparent' : 'var(--color-bg-secondary)',
                      }}
                    >
                      {parsedData.columns.map((col) => (
                        <td
                          key={col}
                          className="px-4 py-2"
                          style={{ color: 'var(--color-text-secondary)' }}
                        >
                          {row[col] || '-'}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Show more indicator */}
            {parsedData.totalRows > 5 && (
              <p 
                className="text-center text-sm"
                style={{ color: 'var(--color-text-secondary)' }}
              >
                Showing 5 of {parsedData.totalRows.toLocaleString()} rows
              </p>
            )}

            {/* Continue Button */}
            <div className="flex justify-end pt-4">
              <Button
                onClick={handleContinue}
                disabled={!parsedData}
              >
                Continue
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}