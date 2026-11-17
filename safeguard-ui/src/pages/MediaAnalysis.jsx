import { useState, useRef, useEffect } from "react";
import { api } from "../api";
import { useToast } from "../components/Toast";

const CAPTURE_DURATION = 15; // seconds

// ─────────────────────────────────────────────────────────────
// Root component
// ─────────────────────────────────────────────────────────────
export default function MediaAnalysis() {
  const toast = useToast();
  const [tab, setTab] = useState("upload");

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Media Analysis</div>
          <div className="page-sub">Upload media or use live camera for AI safety analysis</div>
        </div>
      </div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: 0, marginBottom: 24, borderBottom: "1px solid var(--border)" }}>
        {[
          { id: "upload", label: "📁  Upload File" },
          { id: "live",   label: "📷  Live Camera (15s)" },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding: "9px 20px", fontSize: 13, fontWeight: 500,
            background: "none", border: "none", cursor: "pointer",
            borderBottom: tab === t.id ? "2px solid var(--accent)" : "2px solid transparent",
            color: tab === t.id ? "var(--accent)" : "var(--text2)",
            marginBottom: -1, transition: "color 0.15s",
          }}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "upload" ? <UploadTab toast={toast} /> : <LiveCameraTab toast={toast} />}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Upload Tab  (original — unchanged)
// ─────────────────────────────────────────────────────────────
function UploadTab({ toast }) {
  const fileRef = useRef();
  const [drag, setDrag] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [fileName, setFileName] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isVideo, setIsVideo] = useState(false);

  async function analyze(file) {
    setFileName(file.name);
    setAnalyzing(true);
    setResult(null);
    setProgress(10);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setIsVideo(file.type.startsWith("video/"));
    const ticker = setInterval(() => setProgress(p => Math.min(p + Math.random() * 8, 88)), 800);
    try {
      const res = await api.analyzeFile(file);
      clearInterval(ticker);
      setProgress(100);
      setResult(res);
      const lvl = res.alert_level;
      toast(`Analysis complete — ${lvl}`, lvl === "UNSAFE" ? "error" : lvl === "REVIEW" ? "info" : "success");
    } catch (e) {
      clearInterval(ticker);
      toast(e.message, "error");
    } finally {
      setAnalyzing(false);
    }
  }

  function handleFile(e) { const f = e.target.files[0]; if (f) analyze(f); }
  function handleDrop(e) { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) analyze(f); }

  return (
    <div className="grid-2">
      <div>
        {!previewUrl ? (
          <div
            className={`upload-zone ${drag ? "drag" : ""}`}
            onClick={() => fileRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={handleDrop}
          >
            <input ref={fileRef} type="file" accept=".mp4,.avi,.mov,.mkv,.wav,.mp3" onChange={handleFile} style={{ display: "none" }} />
            <div style={{ fontSize: 32, marginBottom: 12 }}>📁</div>
            <div style={{ fontSize: 14, color: "var(--text0)", fontWeight: 500, marginBottom: 6 }}>Drop video or audio file here</div>
            <div style={{ fontSize: 12, color: "var(--text2)" }}>or click to browse</div>
            <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 10 }}>mp4 · avi · mov · mkv · wav · mp3</div>
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            {isVideo ? (
              <video src={previewUrl} controls style={{ width: "100%", display: "block", borderRadius: "var(--radius-lg)", maxHeight: 280, background: "#000" }} />
            ) : (
              <div style={{ padding: "20px 16px", display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 28 }}>🎵</span>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text0)" }}>{fileName}</div>
                  <audio src={previewUrl} controls style={{ marginTop: 8, width: "100%" }} />
                </div>
              </div>
            )}
            <div style={{ padding: "10px 14px", borderTop: "1px solid var(--border)" }}>
              <button className="btn btn-ghost" style={{ fontSize: 12 }}
                onClick={() => { setPreviewUrl(null); setResult(null); setFileName(null); fileRef.current?.click(); }}>
                ↺ Analyse another file
              </button>
            </div>
            <input ref={fileRef} type="file" accept=".mp4,.avi,.mov,.mkv,.wav,.mp3" onChange={handleFile} style={{ display: "none" }} />
          </div>
        )}

        {analyzing && (
          <div style={{ marginTop: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 12, color: "var(--text2)" }}>
              <span>Analyzing {fileName}…</span><span>{Math.round(progress)}%</span>
            </div>
            <div className="progress-track"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>
            <div style={{ marginTop: 8, fontSize: 11, color: "var(--text2)" }}>
              {progress < 30 ? "Extracting frames…" : progress < 60 ? "Running visual model…" : progress < 85 ? "Transcribing audio…" : "Fusing results…"}
            </div>
          </div>
        )}

        {result && <TranscriptCard result={result} />}
      </div>

      <ResultPanel result={result} />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Live Camera Tab
// ─────────────────────────────────────────────────────────────
function LiveCameraTab({ toast }) {
  const videoRef    = useRef(null);
  const streamRef   = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef   = useRef([]);
  const timerRef    = useRef(null);

  // camState: idle | preview | recording | analyzing | done | error
  const [camState, setCamState]       = useState("idle");
  const [countdown, setCountdown]     = useState(CAPTURE_DURATION);
  const [result, setResult]           = useState(null);
  const [errMsg, setErrMsg]           = useState("");
  const [recordedUrl, setRecordedUrl] = useState(null);
  const [analyzing, setAnalyzing]     = useState(false);
  const [progress, setProgress]       = useState(0);

  useEffect(() => () => stopEverything(), []);

  function stopEverything() {
    if (timerRef.current) clearInterval(timerRef.current);
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      try { recorderRef.current.stop(); } catch (_) {}
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
  }

  async function startCamera() {
    setErrMsg("");
    setResult(null);
    if (recordedUrl) { URL.revokeObjectURL(recordedUrl); setRecordedUrl(null); }
    try {
      // Request video + audio (mic) together
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
        audio: true,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCamState("preview");
    } catch (e) {
      const msg = e.name === "NotAllowedError"
        ? "Camera/mic access denied. Allow permissions in your browser and try again."
        : `Could not start camera: ${e.message}`;
      setErrMsg(msg);
      setCamState("error");
    }
  }

  function startRecording() {
    chunksRef.current = [];
    setCountdown(CAPTURE_DURATION);
    setCamState("recording");

    // Pick best supported MIME (webm with audio is most compatible)
    const mimeType = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,opus",
      "video/webm",
      "video/mp4",
    ].find(m => MediaRecorder.isTypeSupported(m)) || "";

    const recorder = new MediaRecorder(
      streamRef.current,
      mimeType ? { mimeType } : {}
    );
    recorderRef.current = recorder;
    recorder.ondataavailable = e => { if (e.data?.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = () => handleRecordingDone(mimeType);
    recorder.start(200); // chunk every 200ms

    // 1-second countdown
    let elapsed = 0;
    timerRef.current = setInterval(() => {
      elapsed += 1;
      setCountdown(CAPTURE_DURATION - elapsed);
      if (elapsed >= CAPTURE_DURATION) {
        clearInterval(timerRef.current);
        recorder.stop();
        // Release camera after recording
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(t => t.stop());
          streamRef.current = null;
        }
      }
    }, 1000);
  }

  function handleRecordingDone(mimeType) {
    const ext  = mimeType.includes("mp4") ? "mp4" : "webm";
    const blob = new Blob(chunksRef.current, { type: mimeType || "video/webm" });

    // Local playback preview
    const url = URL.createObjectURL(blob);
    setRecordedUrl(url);

    // Animate progress while backend processes
    setAnalyzing(true);
    setProgress(10);
    setCamState("analyzing");
    const ticker = setInterval(() => setProgress(p => Math.min(p + Math.random() * 7, 88)), 800);

    api.analyzeLive(blob, `live.${ext}`)
      .then(res => {
        clearInterval(ticker);
        setProgress(100);
        setResult(res);
        setAnalyzing(false);
        setCamState("done");
        const lvl = res.alert_level;
        toast(`Live analysis complete — ${lvl}`, lvl === "UNSAFE" ? "error" : lvl === "REVIEW" ? "info" : "success");
      })
      .catch(e => {
        clearInterval(ticker);
        setAnalyzing(false);
        setErrMsg(e.message);
        setCamState("error");
        toast(e.message, "error");
      });
  }

  function reset() {
    stopEverything();
    if (recordedUrl) { URL.revokeObjectURL(recordedUrl); setRecordedUrl(null); }
    setResult(null);
    setCountdown(CAPTURE_DURATION);
    setErrMsg("");
    setAnalyzing(false);
    setProgress(0);
    setCamState("idle");
  }

  // SVG countdown ring
  const r    = 28;
  const circ = 2 * Math.PI * r;
  const ringOffset = circ * (1 - countdown / CAPTURE_DURATION);

  return (
    <div className="grid-2">
      {/* ── Left: camera + controls ── */}
      <div>
        {/* Viewport */}
        <div style={{
          position: "relative", background: "#000",
          borderRadius: "var(--radius-lg)", overflow: "hidden", aspectRatio: "16/9",
          border: camState === "recording" ? "2px solid var(--red)" : "2px solid var(--border)",
          transition: "border-color 0.3s",
        }}>
          {/* Live preview */}
          <video ref={videoRef} muted playsInline style={{
            width: "100%", height: "100%", objectFit: "cover", display: "block",
            visibility: (camState === "preview" || camState === "recording") ? "visible" : "hidden",
          }} />

          {/* Recorded playback (shown when done) */}
          {(camState === "done" || camState === "analyzing") && recordedUrl && (
            <video src={recordedUrl} controls={camState === "done"} autoPlay={camState === "analyzing"} muted={camState === "analyzing"} style={{
              position: "absolute", inset: 0,
              width: "100%", height: "100%", objectFit: "cover", background: "#000",
            }} />
          )}

          {/* Idle */}
          {camState === "idle" && (
            <Overlay>
              <span style={{ fontSize: 48 }}>📷</span>
              <div style={{ fontSize: 13, color: "var(--text2)", marginTop: 8 }}>Camera not started</div>
            </Overlay>
          )}

          {/* Error */}
          {camState === "error" && (
            <Overlay>
              <span style={{ fontSize: 36 }}>⚠️</span>
              <div style={{ fontSize: 12, color: "var(--red)", textAlign: "center", marginTop: 8, padding: "0 20px" }}>{errMsg}</div>
            </Overlay>
          )}

          {/* Analysing overlay on top of playback */}
          {camState === "analyzing" && (
            <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.6)", gap: 12 }}>
              <div style={{ width: 36, height: 36, border: "3px solid rgba(255,255,255,0.2)", borderTopColor: "var(--accent)", borderRadius: "50%", animation: "sg-spin 0.8s linear infinite" }} />
              <div style={{ fontSize: 13, color: "#fff" }}>Analysing…</div>
            </div>
          )}

          {/* REC countdown ring */}
          {camState === "recording" && (
            <div style={{ position: "absolute", top: 10, right: 12 }}>
              <svg width={68} height={68} viewBox="0 0 68 68">
                <circle cx="34" cy="34" r={r} fill="rgba(0,0,0,0.6)" stroke="rgba(255,255,255,0.1)" strokeWidth="4" />
                <circle cx="34" cy="34" r={r} fill="none" stroke="var(--red)" strokeWidth="4"
                  strokeDasharray={circ} strokeDashoffset={ringOffset} strokeLinecap="round"
                  transform="rotate(-90 34 34)" style={{ transition: "stroke-dashoffset 0.9s linear" }} />
                <text x="34" y="39" textAnchor="middle" fontSize="18" fontWeight="700" fill="#fff">{countdown}</text>
              </svg>
              <div style={{ position: "absolute", bottom: -4, left: "50%", transform: "translateX(-50%)", background: "var(--red)", color: "#fff", fontSize: 9, fontWeight: 700, padding: "2px 6px", borderRadius: 4, letterSpacing: "0.1em" }}>REC</div>
            </div>
          )}

          {/* Mic indicator */}
          {camState === "recording" && (
            <div style={{ position: "absolute", bottom: 10, left: 12, display: "flex", alignItems: "center", gap: 6, background: "rgba(0,0,0,0.6)", padding: "4px 10px", borderRadius: 20 }}>
              <span style={{ fontSize: 12 }}>🎙</span>
              <span style={{ fontSize: 11, color: "#fff" }}>Mic on</span>
            </div>
          )}
        </div>

        {/* Progress bar during analysis */}
        {analyzing && (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8, fontSize: 12, color: "var(--text2)" }}>
              <span>Running AI pipeline…</span><span>{Math.round(progress)}%</span>
            </div>
            <div className="progress-track"><div className="progress-fill" style={{ width: `${progress}%` }} /></div>
            <div style={{ marginTop: 8, fontSize: 11, color: "var(--text2)" }}>
              {progress < 25 ? "Extracting frames…" : progress < 50 ? "Running visual model…" : progress < 75 ? "Transcribing audio…" : "Fusing results…"}
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: "flex", gap: 10, marginTop: 14 }}>
          {camState === "idle" && (
            <button className="btn btn-primary" style={{ flex: 1 }} onClick={startCamera}>
              🎥  Start Camera & Mic
            </button>
          )}
          {camState === "preview" && (
            <>
              <button className="btn btn-primary" style={{ flex: 1, background: "var(--red)", borderColor: "var(--red)" }} onClick={startRecording}>
                ⏺  Record 15 Seconds
              </button>
              <button className="btn btn-ghost" onClick={reset}>Cancel</button>
            </>
          )}
          {camState === "recording" && (
            <button className="btn btn-ghost" style={{ flex: 1 }} onClick={reset}>✕  Cancel</button>
          )}
          {(camState === "done" || camState === "error") && (
            <button className="btn btn-ghost" style={{ flex: 1 }} onClick={reset}>↺  Record Again</button>
          )}
        </div>

        {/* Info note */}
        {camState === "idle" && (
          <div style={{ marginTop: 14, padding: "10px 14px", background: "var(--bg2)", borderRadius: "var(--radius)", fontSize: 12, color: "var(--text2)", lineHeight: 1.7 }}>
            📌 Records <strong>15 seconds</strong> of webcam video + microphone audio.
          </div>
        )}

        {/* Transcript */}
        {result && <TranscriptCard result={result} />}
      </div>

      {/* ── Right: results ── */}
      <ResultPanel result={result} />

      <style>{`@keyframes sg-spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Shared helpers
// ─────────────────────────────────────────────────────────────

function Overlay({ children }) {
  return (
    <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
      {children}
    </div>
  );
}

function TranscriptCard({ result }) {
  if (!result) return null;
  if (result.transcript) return (
    <div className="card" style={{ marginTop: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12, color: "var(--text0)" }}>Speech Transcript</div>
      <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text1)", lineHeight: 1.8, whiteSpace: "pre-wrap", maxHeight: 200, overflowY: "auto" }}>
        {result.transcript}
      </div>
      {result.toxic_phrases?.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Flagged Phrases</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {result.toxic_phrases.map((p, i) => <span key={i} className="badge badge-red">{p}</span>)}
          </div>
        </div>
      )}
    </div>
  );
  return (
    <div className="card" style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ fontSize: 18 }}>🔇</span>
      <div>
        <div style={{ fontSize: 13, color: "var(--text1)", fontWeight: 500 }}>No audio detected</div>
        <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 2 }}>No speech or audio track found</div>
      </div>
    </div>
  );
}

function ResultPanel({ result }) {
  const visualScore     = result ? (parseFloat(result.visual_score)           || 0) : 0;
  const linguisticScore = result ? (parseFloat(result.toxicity_score)         || 0) : 0;
  const acousticScore   = result ? (parseFloat(result.audio_aggression_score) || 0) : 0;
  const fusedScore      = result ? (parseFloat(result.fused_score)            || 0) : 0;
  const level           = result?.alert_level;

  const EMOTION_EMOJI = { anger: "😠", fear: "😨", disgust: "🤢", sadness: "😢", surprise: "😲", happiness: "😊", neutral: "😐" };

  const chips = [
    result?.fight_ratio != null && {
      icon: "", label: "Fight Ratio",
      value: `${Math.round(parseFloat(result.fight_ratio) * 100)}%`,
    },
    result?.emotion && {
      icon: " ", label: "Emotion",
      value: result.emotion.charAt(0).toUpperCase() + result.emotion.slice(1),
    },
    result?.emotion_source && {
      icon: "", label: "Source",
      value: result.emotion_source,
    },
  ].filter(Boolean);

  if (!result) return (
    <div className="card" style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="empty-state">
        <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
        <p>Results will appear here</p>
      </div>
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {/* Classification banner */}
      <div style={{
        padding: "20px", borderRadius: "var(--radius-lg)", textAlign: "center",
        background: level === "UNSAFE" ? "var(--red-dim)" : level === "REVIEW" ? "var(--amber-dim)" : "var(--green-dim)",
        border: `1px solid ${level === "UNSAFE" ? "rgba(239,68,68,0.3)" : level === "REVIEW" ? "rgba(245,158,11,0.3)" : "rgba(16,185,129,0.3)"}`,
      }}>
        <div style={{ fontSize: 11, color: "var(--text2)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.1em" }}>Classification</div>
        <div style={{ fontSize: 28, fontWeight: 700, fontFamily: "var(--mono)", color: level === "UNSAFE" ? "var(--red)" : level === "REVIEW" ? "var(--amber)" : "var(--green)" }}>
          {level}
        </div>
        {result.frame_count > 0 && (
          <div style={{ fontSize: 11, color: "var(--text2)", marginTop: 6 }}>{result.frame_count} frames · {result.source}</div>
        )}
      </div>

      {/* Primary risk metrics */}
      <div className="card">
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text0)", marginBottom: 14 }}>Risk Breakdown</div>
        <RiskRow label="Visual Risk"         value={visualScore} />
        <RiskRow label="Speech Toxicity" value={linguisticScore} />
        <RiskRow label="Voice Aggression" value={acousticScore} />
        <RiskRow label="Fused Risk"          value={fusedScore} lastRow={chips.length === 0} />

        {/* Secondary chips — Fight Ratio, Emotion, Source */}
        {chips.length > 0 && (
          <div style={{
            display: "flex", flexWrap: "wrap", gap: 6,
            paddingTop: 12, marginTop: 2,
            borderTop: "1px solid var(--border)",
          }}>
            {chips.map((chip, i) => (
              <span key={i} style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                padding: "3px 10px", borderRadius: 20,
                background: "var(--bg3)", border: "1px solid var(--border2)",
                fontSize: 11, color: "var(--text1)",
              }}>
                <span style={{ fontSize: 12 }}>{chip.icon}</span>
                <span style={{ color: "var(--text2)", fontWeight: 500 }}>{chip.label}:</span>
                <span style={{ fontWeight: 600, color: "var(--text0)" }}>{chip.value}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Final confidence — separate card */}
      {result.final_confidence != null && (
        <div className="card">
          <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text0)", marginBottom: 10 }}>Confidence</div>
          <RiskRow label="Final Confidence" value={parseFloat(result.final_confidence) || 0} lastRow />
        </div>
      )}

      {/* Require BOTH an aggression signal AND meaningful toxicity (>15%).
          Pure acoustic aggression (athletic exertion, cheering, grunts) without
          any toxic speech content should NOT trigger this alert. */}
      {(result.is_speech_aggressive || result.is_aggressive) && (parseFloat(result.toxicity_score) || 0) > 0.15 && (
        <div style={{ padding: "10px 14px", borderRadius: "var(--radius)", background: "var(--red-dim)", border: "1px solid rgba(239,68,68,0.25)", fontSize: 12, color: "var(--red)", fontWeight: 500 }}>
          ⚠ Aggressive speech detected
        </div>
      )}

      {result.errors?.length > 0 && (
        <div className="card" style={{ borderColor: "rgba(239,68,68,0.2)" }}>
          <div style={{ fontSize: 12, color: "var(--red)", fontWeight: 600, marginBottom: 6 }}>Pipeline warnings</div>
          {result.errors.map((e, i) => <div key={i} style={{ fontSize: 11, color: "var(--text2)" }}>{e}</div>)}
        </div>
      )}
    </div>
  );
}

function RiskRow({ label, value, lastRow = false }) {
  const color = value >= 0.75 ? "var(--red)" : value >= 0.55 ? "var(--amber)" : "var(--green)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: lastRow ? 0 : 12 }}>
      <div style={{ width: 148, fontSize: 12, color: "var(--text2)", flexShrink: 0 }}>{label}</div>
      <div style={{ flex: 1, height: 6, background: "var(--bg4)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ width: `${Math.round(value * 100)}%`, height: "100%", background: color, borderRadius: 3 }} />
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color, fontFamily: "var(--mono)", minWidth: 36, textAlign: "right" }}>
        {Math.round(value * 100)}%
      </div>
    </div>
  );
}
