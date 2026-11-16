"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BookOpen, Boxes, CircleHelp, Home, Layers3, Map, Plus, Search, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const workspaceItems = [
  { name: "Workspace", href: "/", icon: Home },
  { name: "Maps", href: "/scenes", icon: Map },
  { name: "Create map", href: "/upload", icon: Plus },
  { name: "Test localization", href: "/localize", icon: Search },
];
const developerItems = [
  { name: "Analytics", href: "/analytics", icon: Activity },
  { name: "Developer settings", href: "/settings", icon: Settings },
];

function isCurrent(pathname: string, href: string) {
  return href === "/" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
}

function NavItem({ item, pathname }: { item: (typeof workspaceItems)[number]; pathname: string }) {
  const active = isCurrent(pathname, item.href);
  return <Link href={item.href} className={cn("flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors", active ? "bg-indigo-50 text-indigo-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-950")}><item.icon className="h-4 w-4" aria-hidden="true" />{item.name}</Link>;
}

export default function Navbar() {
  const pathname = usePathname();
  return <>
    <header className="fixed inset-x-0 top-0 z-40 h-16 border-b border-slate-200 bg-white/95 backdrop-blur md:left-64">
      <div className="flex h-full items-center justify-between px-4 sm:px-8">
        <div className="flex items-center gap-2 text-sm text-slate-500 md:hidden"><Layers3 className="h-5 w-5 text-indigo-600" /><span className="font-semibold text-slate-900">VPS Studio</span></div>
        <div className="hidden text-sm text-slate-500 md:block">Spatial mapping workspace</div>
        <div className="flex items-center gap-3"><div className="hidden text-right sm:block"><p className="text-xs font-semibold text-slate-800">Pilot workspace</p><p className="text-xs text-slate-500">Local development</p></div><div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">VP</div></div>
      </div>
    </header>
    <aside className="fixed inset-y-0 left-0 z-50 hidden w-64 border-r border-slate-200 bg-white md:flex md:flex-col">
      <Link href="/" className="flex h-16 items-center gap-3 border-b border-slate-200 px-6"><div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white"><Boxes className="h-5 w-5" /></div><span className="text-lg font-bold tracking-tight text-slate-950">VPS Studio</span></Link>
      <nav className="flex-1 px-3 py-6" aria-label="Main navigation"><p className="px-3 pb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Workspace</p><div className="space-y-1">{workspaceItems.map((item) => <NavItem key={item.href} item={item} pathname={pathname} />)}</div><p className="px-3 pb-2 pt-7 text-xs font-semibold uppercase tracking-wider text-slate-400">Developer</p><div className="space-y-1">{developerItems.map((item) => <NavItem key={item.href} item={item} pathname={pathname} />)}</div></nav>
      <div className="border-t border-slate-200 p-3"><a href="/docs/quickstart" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"><BookOpen className="h-4 w-4" />Documentation</a><a href="mailto:support@example.com" className="mt-1 flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-600 hover:bg-slate-100"><CircleHelp className="h-4 w-4" />Support</a></div>
    </aside>
  </>;
}
