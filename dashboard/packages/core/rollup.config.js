import terser from "@rollup/plugin-terser";
import typescript from "@rollup/plugin-typescript";
import json from "@rollup/plugin-json";
import { nodeResolve } from '@rollup/plugin-node-resolve';
import { defineConfig } from "rollup";

const createConfig = ({ 
  input,
  output,
  typescriptPluginConfig = {
    tsconfig: "./tsconfig.json",
    include: ["./src/**/*.ts", "./src/**/*.json"],
  },
}) => defineConfig({
  input,
  output,
  plugins: [
    nodeResolve({
      preferBuiltins: true,
      extensions: ['.ts', '.js']
    }),
    typescript({
      ...typescriptPluginConfig,
    }),
    terser({
      toplevel: true,
    }),
    json(),
  ],
  external: [
    'lodash-es',
    'luxon'
  ],
});

export default [
  createConfig({
    input: "src/index.ts",
    output: {
      format: "es",
      file: "lib/esm/index.mjs",
      name: "core",
    },
    typescriptPluginConfig: {
      tsconfig: "./tsconfig.json",
      include: ["./src/**/*.ts", "./src/**/*.json"],
      compilerOptions: {
        outDir: "./lib/esm",
        module: "NodeNext",
        moduleResolution: "NodeNext",
        lib: ["esnext", "dom"]
      },
    }
  }),
];