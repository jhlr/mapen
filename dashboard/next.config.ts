import type { NextConfig } from "next";

// authInterrupts (experimental no Next): permite unauthorized() mostrar app/unauthorized.tsx com HTTP 401.
const config: NextConfig = { experimental: { authInterrupts: true } };

export default config;
