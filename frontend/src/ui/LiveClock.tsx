import { useEffect, useState } from "react";

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

/** Live local time, echoing the reference site's "HCMC, 15:26" status ticker. */
export default function LiveClock({ label = "LOCAL" }: { label?: string }) {
  const [time, setTime] = useState(() => formatTime(new Date()));

  useEffect(() => {
    const interval = window.setInterval(() => setTime(formatTime(new Date())), 15000);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <span className="clock" aria-label={`Local time ${time}`}>
      <span className="clock__dot" aria-hidden="true" />
      {label}
      <span className="clock__time">{time}</span>
    </span>
  );
}
