import { useEffect, useState } from "react";

import { parseRoute } from "../router";
import type { Route } from "../router";

export function useHashRoute(): Route {
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));

  useEffect(() => {
    const handleChange = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", handleChange);
    return () => window.removeEventListener("hashchange", handleChange);
  }, []);

  return route;
}
