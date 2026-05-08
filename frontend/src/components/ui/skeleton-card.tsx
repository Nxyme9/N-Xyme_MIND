import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface SkeletonCardProps {
  hasHeader?: boolean;
  headerTitle?: string;
  contentLines?: number;
  className?: string;
}

export function SkeletonCard({
  hasHeader = true,
  headerTitle,
  contentLines = 3,
  className,
}: SkeletonCardProps) {
  return (
    <Card className={className}>
      {hasHeader && (
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-32" />
          {headerTitle && (
            <p className="text-sm text-muted-foreground">{headerTitle}</p>
          )}
        </CardHeader>
      )}
      <CardContent>
        <div className="space-y-2">
          {Array.from({ length: contentLines }).map((_, i) => (
            <Skeleton
              key={i}
              className="h-4"
              style={{ width: `${100 - i * 15}%` }}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-8 w-8 rounded-full" />
        </div>
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16 mb-2" />
        <Skeleton className="h-3 w-24" />
      </CardContent>
    </Card>
  );
}
