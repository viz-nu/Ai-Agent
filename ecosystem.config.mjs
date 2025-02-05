export default {
  apps: [
    {
      name: "my-app",
      script: "./src/index.js",
      node_args: "-r dotenv/config",
      env: {
        NODE_ENV: "production",
      },
    },
  ],
};