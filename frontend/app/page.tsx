import Link from 'next/link';
import { ArrowRight, Layers, MapPin, Search, Cpu, Globe } from 'lucide-react';

export default function Home() {
  return (
    <div className="relative isolate overflow-hidden">
      {/* Background decoration */}
      <div className="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80">
        <div className="relative left-[calc(50%-11rem)] aspect-[1155/678] w-[36.125rem] -translate-x-1/2 rotate-[30deg] bg-gradient-to-tr from-[#ff80b5] to-[#9089fc] opacity-20 sm:left-[calc(50%-30rem)] sm:w-[72.1875rem]" />
      </div>

      <div className="mx-auto max-w-7xl px-6 pb-24 pt-10 sm:pb-32 lg:flex lg:px-8 lg:pt-40">
        <div className="mx-auto max-w-2xl flex-shrink-0 lg:mx-0 lg:max-w-xl lg:pt-8">
          <div className="mt-24 sm:mt-32 lg:mt-16">
            <a href="#" className="inline-flex space-x-6">
              <span className="rounded-full bg-indigo-600/10 px-3 py-1 text-sm font-semibold leading-6 text-indigo-600 ring-1 ring-inset ring-indigo-600/10">
                What's New
              </span>
              <span className="inline-flex items-center space-x-2 text-sm font-medium leading-6 text-gray-600">
                <span>v0.1.0 MVP Live</span>
                <ArrowRight className="h-4 w-4 text-gray-400" />
              </span>
            </a>
          </div>
          <h1 className="mt-10 text-4xl font-black tracking-tighter text-gray-900 sm:text-7xl uppercase">
            Clinical Precision <br/> for <span className="text-indigo-600">Spatial Health</span>
          </h1>
          <p className="mt-6 text-xl leading-8 text-gray-600 font-medium">
            Convert hospital wings into sub-decimeter VPS maps. 
            Achieve <span className="bg-indigo-50 text-indigo-700 px-2 rounded-lg font-black tracking-tight">4.1cm Accuracy</span> in low-parallax indoor environments.
          </p>
          <div className="mt-10 flex items-center gap-x-6">
            <Link
              href="/upload"
              className="rounded-xl bg-indigo-600 px-8 py-4 text-lg font-bold text-white shadow-xl shadow-indigo-200 hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 transition-all"
            >
              Start Mapping
            </Link>
            <Link href="/dashboard" className="text-sm font-bold leading-6 text-gray-900 flex items-center group">
              View Benchmarks <span className="ml-2 transition-transform group-hover:translate-x-1">→</span>
            </Link>
          </div>
        </div>
        
        <div className="mx-auto mt-16 flex max-w-2xl sm:mt-24 lg:ml-10 lg:mr-0 lg:mt-0 lg:max-w-none lg:flex-none xl:ml-32">
          <div className="max-w-3xl flex-none sm:max-w-5xl lg:max-w-none">
            <div className="rounded-3xl bg-gray-900/5 p-2 ring-1 ring-inset ring-gray-900/10 lg:-m-4 lg:rounded-[2.5rem] lg:p-4 shadow-2xl">
              <div className="bg-white rounded-2xl shadow-inner p-8 grid grid-cols-2 gap-6 w-full lg:w-[480px]">
                <FeatureItem icon={<MapPin />} title="Sub-cm Pose" desc="Precise 6DoF estimation" />
                <FeatureItem icon={<Cpu />} title="Web GPU" titleColor="text-orange-600" desc="Real-time splat rendering" />
                <FeatureItem icon={<Search />} title="ORB Indexing" desc="Fast descriptor retrieval" />
                <FeatureItem icon={<Globe />} title="Open API" desc="Anchor objects anywhere" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function FeatureItem({ icon, title, titleColor = "text-indigo-600", desc }: any) {
  return (
    <div className="p-4 rounded-xl bg-gray-50 border border-gray-100 italic transition-transform hover:-translate-y-1">
      <div className={`mb-2 font-bold flex items-center ${titleColor}`}>
        <span className="mr-2 opacity-70 scale-75">{icon}</span>
        {title}
      </div>
      <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">{desc}</div>
    </div>
  );
}
