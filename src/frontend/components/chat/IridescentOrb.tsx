"use client";

import React from "react";

export function IridescentOrb() {
  return (
    <div className="relative flex items-center justify-center p-4">
      {/* Ambient background blur diffusion */}
      <div className="absolute w-24 h-24 rounded-full bg-brand-400/20 blur-2xl pointer-events-none animate-pulse-slow" />
      
      {/* 3D Iridescent Orb */}
      <div className="orb-3d animate-float-subtle relative z-10 flex items-center justify-center cursor-pointer transition-transform duration-300 hover:scale-105 active:scale-95">
        {/* Subtle inner refraction ring */}
        <div className="w-10 h-10 rounded-full border border-white/30 opacity-60 pointer-events-none" />
      </div>
    </div>
  );
}
