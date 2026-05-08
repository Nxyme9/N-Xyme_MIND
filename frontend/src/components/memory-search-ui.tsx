"use client";

import { useState, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { Search, X, Loader2 } from "lucide-react";

interface MemorySearchResult {
  id: string;
  content: string;
  type: string;
  timestamp?: string;
  trust: number;
}

interface MemorySearchUIProps {
  className?: string;
  onResultClick?: (result: MemorySearchResult) => void;
  placeholder?: string;
}

export function MemorySearchUI({ className, onResultClick, placeholder = "Search memories..." }: MemorySearchUIProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MemorySearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;

    setIsSearching(true);
    setHasSearched(true);

    try {
      const res = await fetch(`/api/memory/search?q=${encodeURIComponent(query)}`, {
        signal: AbortSignal.timeout(10000),
      });
      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
      } else {
        setResults([]);
      }
    } catch (e) {
      console.error("Search failed:", e);
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const handleClear = () => {
    setQuery("");
    setResults([]);
    setHasSearched(false);
  };

  const getTrustColor = (trust: number) => {
    if (trust >= 0.9) return "text-green-500";
    if (trust >= 0.7) return "text-yellow-500";
    return "text-red-500";
  };

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="pl-10 pr-10"
          />
          {query && (
            <button
              onClick={handleClear}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <Button onClick={handleSearch} disabled={isSearching || !query.trim()}>
          {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : "Search"}
        </Button>
      </div>

      {hasSearched && !isSearching && (
        <div className="text-sm text-muted-foreground">
          {results.length === 0 ? (
            <p>No memories found for "{query}"</p>
          ) : (
            <p>{results.length} result{results.length !== 1 ? "s" : ""} found</p>
          )}
        </div>
      )}

      <div className="space-y-2">
        {results.map((result) => (
          <Card
            key={result.id}
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => onResultClick?.(result)}
          >
            <CardContent className="p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm line-clamp-2">{result.content}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span className="capitalize">{result.type}</span>
                    {result.timestamp && (
                      <>
                        <span>•</span>
                        <span>{new Date(result.timestamp).toLocaleDateString()}</span>
                      </>
                    )}
                  </div>
                </div>
                <span className={cn("text-xs font-mono", getTrustColor(result.trust))}>
                  {(result.trust * 100).toFixed(0)}%
                </span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export function MemorySearchMini() {
  const [isOpen, setIsOpen] = useState(false);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 left-4 z-40 flex items-center gap-2 px-3 py-2 rounded-full bg-card border border-border shadow-lg hover:border-primary/50 transition-colors"
      >
        <Search className="w-4 h-4" />
        <span className="text-sm">Search Memory</span>
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm" onClick={() => setIsOpen(false)}>
      <div
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <MemorySearchUI onResultClick={() => setIsOpen(false)} />
        <Button variant="ghost" className="mt-4 w-full" onClick={() => setIsOpen(false)}>
          Close
        </Button>
      </div>
    </div>
  );
}