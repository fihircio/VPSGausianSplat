"use client";

import { cn } from '@/lib/utils';
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';

type Status = 'UPLOADED' | 'QUEUED' | 'PROCESSING' | 'READY' | 'FAILED';

const stages: { key: Status; label: string }[] = [
  { key: 'UPLOADED', label: 'Uploaded' },
  { key: 'QUEUED', label: 'Queued' },
  { key: 'PROCESSING', label: 'Processing' },
  { key: 'READY', label: 'Ready' },
];

export default function SceneStatusTimeline({ status }: { status: Status }) {
  const currentIdx = stages.findIndex(s => s.key === status);
  const isFailed = status === 'FAILED';

  return (
    <div className="w-full py-6">
      <div className="flex items-center justify-between">
        {stages.map((stage, idx) => {
          const isCompleted = currentIdx > idx || status === 'READY';
          const isCurrent = currentIdx === idx && !isFailed;
          const isPending = currentIdx < idx && !isFailed;
          const isError = isFailed && idx === currentIdx;

          return (
            <div key={stage.key} className="flex flex-col items-center flex-1 relative">
              {/* Connector Line */}
              {idx < stages.length - 1 && (
                <div className={cn(
                  "absolute h-0.5 w-[calc(100%-2rem)] top-4 translate-x-1/2 left-0 transition-colors duration-500",
                  isCompleted ? "bg-indigo-600" : "bg-gray-200"
                )} />
              )}

              {/* Icon */}
              <div className="relative z-10 transition-all duration-300">
                {isCompleted ? (
                  <CheckCircle2 className="h-8 w-8 text-indigo-600 bg-white" />
                ) : isCurrent ? (
                  <Loader2 className="h-8 w-8 text-indigo-600 bg-white animate-spin" />
                ) : isError ? (
                  <XCircle className="h-8 w-8 text-red-600 bg-white" />
                ) : (
                  <Circle className="h-8 w-8 text-gray-300 bg-white fill-gray-50" />
                )}
              </div>

              {/* Label */}
              <span className={cn(
                "mt-2 text-xs font-semibold uppercase tracking-wider",
                isCurrent ? "text-indigo-600" : isCompleted ? "text-gray-900" : "text-gray-400"
              )}>
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
