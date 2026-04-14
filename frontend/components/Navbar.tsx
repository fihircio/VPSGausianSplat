"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { Layers, Upload, Search, BarChart3, Home, Maximize } from 'lucide-react';

const navItems = [
  { name: 'Home', href: '/', icon: Home },
  { name: '3D Explorer', href: '/scenes', icon: Maximize },
  { name: 'Upload', href: '/upload', icon: Upload },
  { name: 'Test VPS', href: '/localize', icon: Search },
  { name: 'Investor Deck', href: '/dashboard', icon: BarChart3 },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-gray-200 bg-white sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex items-center">
            <Link href="/" className="flex items-center space-x-2">
              <Layers className="h-8 w-8 text-indigo-600" />
              <span className="text-xl font-bold text-gray-900 tracking-tight">VPS Cloud</span>
            </Link>
          </div>
          <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
            {navItems.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors",
                  pathname === item.href
                    ? "border-indigo-500 text-gray-900"
                    : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                )}
              >
                <item.icon className="h-4 w-4 mr-2" />
                {item.name}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}
