import { safeLocal, storedJson, storageFailed, subscribeStorage } from "../storageModel.mjs";
import React from "react";

import { useEffect, useState, useRef } from "react";

export const INITIAL_MESSAGES = [
  {
    role: "assistant",
    text: "Ask which Wits modules you can take, or share your interests for module and elective suggestions.",
    suggestions: [
      "module eligibility",
      "Recommend EFA04 year 4 electives for machine learning",
      "Which third-year modules am I eligible for?",
    ],
  },
];

export const INTERESTS = [
  ["machine_learning", "Machine learning"],
  ["software", "Software development"],
  ["electric_circuits", "Electric circuits"],
  ["control", "Control systems"],
  ["communications", "Communications"],
  ["networking", "Networking"],
  ["cybersecurity", "Cybersecurity"],
  ["data_science", "Data science"],
];

export const CAREER_GOALS = [
  ["graduate_engineer", "Graduate engineer"],
  ["postgraduate_study", "Postgraduate study"],
  ["data_science", "Data or ML role"],
  ["embedded_systems", "Embedded systems"],
  ["product_systems", "Product and systems"],
];

export const titleCase = (value) =>
  String(value ?? "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

export const moduleCodes = (value) => [
  ...new Set(
    String(value ?? "")
      .split(/[\s,;]+/)
      .map((code) => code.trim().toUpperCase())
      .filter(Boolean),
  ),
];

export function readJson(key,fallback){return storedJson(key,fallback);}
export function useStorageFailure(){const [failed,setFailed]=useState(storageFailed);useEffect(()=>{setFailed(storageFailed());return subscribeStorage(()=>setFailed(storageFailed()));},[]);return failed;}

export { getJson } from "../requestJson.mjs";

export function AsyncPanel({ loading = false, title, error, onRetry }) {
  return (
    <section
      className={`async-panel ${loading ? "is-loading" : ""}`}
      role={error ? "alert" : "status"}
      aria-busy={loading}
    >
      <div className="async-symbol" aria-hidden="true">
        {error ? "!" : <span />}
      </div>
      <strong>{title}</strong>
      {error ? (
        <>
          <p>{error}</p>
          <button className="secondary-button" onClick={onRetry}>
            Try again
          </button>
        </>
      ) : (
        <div className="async-skeleton" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      )}
    </section>
  );
}

export function CopyButton({ text, label = "Copy answer" }) {
  const [status, setStatus] = useState("");
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setStatus("Copied");
    } catch {
      setStatus("Copy unavailable. Select the text to copy it.");
    }
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setStatus(""), 4000);
  };
  return (
    <span className="copy-action">
      <button className="text-button" onClick={copy}>
        {label}
      </button>
      <small role="status" aria-live="polite">
        {status}
      </small>
    </span>
  );
}

export function downloadText(filename, text, mime="text/plain") {
  const url = URL.createObjectURL(
    new Blob([text], { type: `${mime};charset=utf-8` }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function usePersistentState(key, initialValue) {
  const [value,setValue]=useState(()=>readJson(key,initialValue));
  const [status,setStatus]=useState('saved');
  useEffect(()=>{setStatus(safeLocal.setItem(key,JSON.stringify(value))?'saved':'error');},[key,value]);
  return [value,setValue,status];
}

export function usePersistentString(key, initialValue = "") {
  const [value, setValue] = useState(
    () => {const value=safeLocal.getItem(key);const allowed={"curricupath-theme":["dark","light"],"curricupath-motion":["off","subtle","expressive","auto","reduced"],"curricupath-advisor-system-v2":["curricupath","handbook_rag"]}[key];return value && (!allowed || allowed.includes(value))?value:initialValue;},
  );
  useEffect(() => {
    if (value) safeLocal.setItem(key, value);
    else safeLocal.removeItem(key);
  }, [key, value]);
  return [value, setValue];
}

export function Stars({ rating, scale = 5 }) {
  const percentage = Math.max(
    0,
    Math.min(100, (Number(rating) / Number(scale || 5)) * 100),
  );
  return (
    <span
      className="rating-display"
      aria-label={`Rated ${rating} out of ${scale}`}
    >
      <span className="stars" aria-hidden="true">
        <span>★★★★★</span>
        <span className="stars-fill" style={{ width: `${percentage}%` }}>
          ★★★★★
        </span>
      </span>
      <span className="rating-number">
        {rating}/{scale}
      </span>
    </span>
  );
}

export function StatusPill({ children, tone = "blue" }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}
