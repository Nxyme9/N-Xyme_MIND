import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export function ChatSkeleton() {
  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <div className="flex-1 flex flex-col">
        <div className="border-b p-4">
          <div className="flex items-center gap-4">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div>
              <Skeleton className="h-5 w-32 mb-1" />
              <Skeleton className="h-3 w-24" />
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className={`flex ${i % 2 === 0 ? "justify-start" : "justify-end"}`}
            >
              <div
                className={`max-w-[70%] ${i % 2 === 0 ? "bg-muted" : "bg-primary"} rounded-lg p-4`}
              >
                <Skeleton className="h-4 w-64 mb-1" />
                <Skeleton className="h-4 w-48" />
              </div>
            </div>
          ))}
        </div>

        <div className="border-t p-4">
          <div className="flex gap-2">
            <Skeleton className="h-10 flex-1" />
            <Skeleton className="h-10 w-24" />
          </div>
        </div>
      </div>

      <div className="w-80 border-l p-4 hidden lg:block">
        <Card>
          <CardHeader className="pb-2">
            <Skeleton className="h-5 w-24" />
          </CardHeader>
          <CardContent className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-4 w-full" />
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
