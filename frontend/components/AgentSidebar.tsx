"use client";

import { motion, AnimatePresence } from 'framer-motion';
import { Users, User, Circle, ShieldCheck } from 'lucide-react';
import { ActiveAgent } from '@/types';
import { cn } from '@/lib/utils';

interface AgentSidebarProps {
  isOpen: boolean;
  agents: ActiveAgent[];
}

export default function AgentSidebar({ isOpen, agents }: AgentSidebarProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
          className="absolute top-32 right-8 w-80 z-40"
        >
          <div className="glass-card bg-black/60 backdrop-blur-3xl border-white/10 rounded-[32px] overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-white/5 bg-white/5">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-indigo-500/20 rounded-xl">
                    <Users className="h-5 w-5 text-indigo-400" />
                  </div>
                  <h2 className="text-white font-bold tracking-tight">Active Agents</h2>
                </div>
                <div className="px-2 py-1 bg-green-500/10 border border-green-500/20 rounded-md">
                  <span className="text-[10px] font-black text-green-400 uppercase tracking-tighter">Live</span>
                </div>
              </div>
            </div>

            <div className="p-4 space-y-3 max-h-[500px] overflow-y-auto custom-scrollbar">
              {agents.length === 0 ? (
                <div className="py-12 text-center">
                  <Users className="h-12 w-12 text-white/5 mx-auto mb-4" />
                  <p className="text-[11px] font-medium text-white/20 uppercase tracking-widest">No agents detected</p>
                </div>
              ) : (
                agents.map((agent) => (
                  <motion.div
                    key={agent.id}
                    initial={{ scale: 0.95, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="p-4 bg-white/[0.03] border border-white/5 rounded-2xl hover:bg-white/[0.06] transition-colors group"
                  >
                    <div className="flex items-start space-x-4">
                      <div className="relative">
                        <div className={cn(
                          "h-10 w-10 rounded-full flex items-center justify-center bg-indigo-500/10 border border-indigo-500/20 group-hover:border-indigo-500/40 transition-colors",
                          agent.role === 'Doctor' ? 'bg-indigo-500/10' : 'bg-emerald-500/10'
                        )}>
                          <User className="h-5 w-5 text-white/70" />
                        </div>
                        <div className="absolute -bottom-0.5 -right-0.5 h-3 w-3 bg-[#050505] rounded-full flex items-center justify-center">
                           <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                           <p className="text-sm font-bold text-white truncate">{agent.name}</p>
                           {agent.role === 'Admin' && <ShieldCheck className="h-3 w-3 text-indigo-400" />}
                        </div>
                        <p className="text-[10px] font-medium text-white/40 uppercase tracking-wider mt-0.5">{agent.role}</p>
                        <div className="flex items-center space-x-2 mt-2">
                           <Circle className="h-1.5 w-1.5 fill-indigo-500 text-indigo-500" />
                           <p className="text-[9px] font-mono text-white/30 truncate">
                             {agent.position.map(v => v.toFixed(2)).join(', ')}
                           </p>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>

            <div className="p-6 bg-white/[0.02] border-t border-white/5">
               <p className="text-[10px] font-medium text-white/20 uppercase tracking-[0.2em] text-center">Spatial Sync Frequency: 60Hz</p>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
