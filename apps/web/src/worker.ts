import app from "vinext/server/fetch-handler";

interface WorkerEnv {
  SKILLWORTH_API_URL?: string;
}

const worker = {
  async fetch(
    request: Request,
    env: WorkerEnv,
    ctx: Parameters<typeof app.fetch>[2],
  ): Promise<Response> {
    const requestUrl = new URL(request.url);
    if (!requestUrl.pathname.startsWith("/backend-api/")) {
      return app.fetch(request, env, ctx);
    }

    if (!env.SKILLWORTH_API_URL) {
      return Response.json({ detail: "Backend API is not configured." }, { status: 503 });
    }

    const target = new URL(
      `${requestUrl.pathname.slice("/backend-api".length)}${requestUrl.search}`,
      env.SKILLWORTH_API_URL,
    );
    return fetch(new Request(target, request));
  },
};

export default worker;
