let webglSupport;
export const hasWebGL = () => {
  if (webglSupport !== undefined) return webglSupport;
  try {
    const c = document.createElement("canvas");
    const context =
      window.WebGLRenderingContext &&
      (c.getContext("webgl") || c.getContext("experimental-webgl"));
    webglSupport = Boolean(context);
    context?.getExtension("WEBGL_lose_context")?.loseContext();
    return webglSupport;
  } catch {
    webglSupport = false;
    return webglSupport;
  }
};
