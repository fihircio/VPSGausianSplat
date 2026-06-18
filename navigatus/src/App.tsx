import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Search,
  MapPin,
  Navigation,
  Camera,
  Video,
  ArrowUp,
  ArrowRight,
  ArrowLeft,
  CheckCircle,
  Info,
  X,
  Map as MapIcon,
  Sparkles,
  Bot,
  MessageSquare,
  Loader2,
  Upload,
  Square,
  Check,
  AlertCircle,
  Settings2,
} from "lucide-react";
import {
  getDefaultSceneId,
  getDemoQueryImageUrl,
  getVpsApiBaseUrl,
  localizeDemoQueryImage,
  localizeVideoFrame,
  localizeMultiVideoFrame,
  VpsLocalizationResult,
  VpsStatus,
} from "./lib/vpsClient";

type Screen =
  | "splash"
  | "home"
  | "search"
  | "ai-assistant"
  | "route-info"
  | "ar-view"
  | "record";

type Destination = {
  id: number;
  name: string;
  department: string;
  distance: string;
  estTime: string;
  vpsSceneId?: string;
  vpsSceneLabel?: string;
};

type AiDestinationResponse = {
  destinationId: number;
  replyMessage: string;
};

type VpsSource = "none" | "live" | "demo";

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>("splash");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDestination, setSelectedDestination] = useState<Destination | null>(null);

  // AI Assistant States
  const [aiInput, setAiInput] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiMessage, setAiMessage] = useState<string | null>(null);

  // AR Simulation States
  const [arStep, setArStep] = useState(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [vpsStatus, setVpsStatus] = useState<VpsStatus>("idle");
  const [vpsResult, setVpsResult] = useState<VpsLocalizationResult | null>(null);
  const [vpsError, setVpsError] = useState<string | null>(null);
  const [vpsSource, setVpsSource] = useState<VpsSource>("none");
  const [isLocalizing, setIsLocalizing] = useState(false);
  const isLocalizingRef = useRef(false);
  const initialMultiFrameDoneRef = useRef(false);
  const [autoLocalize, setAutoLocalize] = useState(true);
  const defaultSceneId = getDefaultSceneId();

  // Recording States
  const recordVideoRef = useRef<HTMLVideoElement | null>(null);
  const recordStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<number | null>(null);
  const [recordingState, setRecordingState] = useState<"idle" | "countdown" | "recording" | "uploading" | "done" | "error">("idle");
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<{ id: string; name: string } | null>(null);
  const [recordingError, setRecordingError] = useState<string | null>(null);
  const [countdownValue, setCountdownValue] = useState(3);
  const [recordSettingsOpen, setRecordSettingsOpen] = useState(false);
  const [recordResolution, setRecordResolution] = useState<"1080p" | "720p" | "480p">("1080p");
  const recordResolutionRef = useRef(recordResolution);
  useEffect(() => { recordResolutionRef.current = recordResolution; }, [recordResolution]);

  const RESOLUTION_MAP: Record<string, { width: number; height: number; label: string }> = {
    "1080p": { width: 1920, height: 1080, label: "1080p Full HD" },
    "720p": { width: 1280, height: 720, label: "720p HD" },
    "480p": { width: 640, height: 480, label: "480p SD" },
  };

  // Mock Data untuk destinasi di Hospital
  const destinations: Destination[] = [
    {
      id: 1,
      name: "Farmasi Pesakit Luar",
      department: "Aras G, Blok A",
      distance: "120m",
      estTime: "2 minit",
      vpsSceneId: defaultSceneId,
      vpsSceneLabel: "Real World Final Demo",
    },
    {
      id: 2,
      name: "Klinik Pakar Bedah",
      department: "Aras 2, Blok B",
      distance: "350m",
      estTime: "5 minit",
    },
    {
      id: 3,
      name: "Wad Kecemasan (ED)",
      department: "Aras G, Blok C",
      distance: "50m",
      estTime: "1 minit",
    },
    {
      id: 4,
      name: "Kaunter Hasil / Pembayaran",
      department: "Aras G, Blok A",
      distance: "80m",
      estTime: "1 minit",
    },
    {
      id: 5,
      name: "Klinik Ortopedik",
      department: "Aras 1, Blok B",
      distance: "200m",
      estTime: "3 minit",
    },
  ];

  // Mock Data untuk Step-by-Step AR Route (Wizard of Oz technique)
  const arRouteSteps = [
    {
      text: "Jalan Terus menyusuri lorong utama",
      distance: "50m",
      icon: (
        <ArrowUp
          size={80}
          className="text-white drop-shadow-lg"
        />
      ),
    },
    {
      text: "Belok Kanan di hadapan Lif Utama",
      distance: "20m",
      icon: <ArrowRight size={80} className="text-white drop-shadow-lg" />,
    },
    {
      text: "Jalan Terus ke hujung lorong",
      distance: "40m",
      icon: <ArrowUp size={80} className="text-white drop-shadow-lg" />,
    },
    {
      text: "Belok Kiri masuk ke Ruang Menunggu",
      distance: "10m",
      icon: <ArrowLeft size={80} className="text-white drop-shadow-lg" />,
    },
    {
      text: "Anda telah tiba di destinasi!",
      distance: "0m",
      icon: <CheckCircle size={80} className="text-green-400 drop-shadow-lg" />,
    },
  ];

  // Splash Screen Timer
  useEffect(() => {
    if (currentScreen === "splash") {
      const timer = setTimeout(() => setCurrentScreen("home"), 2500);
      return () => clearTimeout(timer);
    }
  }, [currentScreen]);

  // Handle Camera for AR Simulation
  useEffect(() => {
    if (currentScreen === "ar-view") {
      startCamera();
    } else if (currentScreen !== "record") {
      initialMultiFrameDoneRef.current = false;
      setVpsStatus("idle");
      setVpsError(null);
      setVpsSource("none");
      setIsLocalizing(false);
      isLocalizingRef.current = false;
      stopCamera();
    }
    return () => {
      if (currentScreen !== "record") stopCamera();
    };
  }, [currentScreen]);

  // Handle Camera for Recording
  useEffect(() => {
    if (currentScreen === "record") {
      startRecordCamera();
    } else {
      stopRecordCamera();
    }
    return () => stopRecordCamera();
  }, [currentScreen]);

  // Multi-frame warmup: collect 4 frames silently before first localization
  useEffect(() => {
    if (currentScreen !== "ar-view" || !cameraActive || initialMultiFrameDoneRef.current) {
      return;
    }

    const warmup = async () => {
      const sceneId = selectedDestination?.vpsSceneId || getDefaultSceneId();
      if (!sceneId || !videoRef.current) {
        initialMultiFrameDoneRef.current = true;
        return;
      }
      if (isLocalizingRef.current) return;

      isLocalizingRef.current = true;
      setIsLocalizing(true);
      setVpsStatus("localizing");
      setVpsSource("live");

      try {
        const result = await localizeMultiVideoFrame({
          video: videoRef.current,
          sceneId,
          frameCount: 4,
          intervalMs: 500,
          agentId: "navigatus-demo-agent",
          apiBaseUrl: getVpsApiBaseUrl(),
        });
        setVpsResult(result);
        setVpsStatus(result.status);
      } catch (err) {
        console.warn("Multi-frame warmup failed, falling back to single-frame", err);
      } finally {
        initialMultiFrameDoneRef.current = true;
        isLocalizingRef.current = false;
        setIsLocalizing(false);
      }
    };

    warmup();
  }, [currentScreen, cameraActive, selectedDestination]);

  useEffect(() => {
    if (currentScreen !== "ar-view" || !cameraActive || !autoLocalize) {
      return;
    }

    const run = () => {
      if (!isLocalizingRef.current) {
        localizeCurrentCameraFrame();
      }
    };

    run();
    const interval = window.setInterval(run, 4000);
    return () => window.clearInterval(interval);
  }, [currentScreen, cameraActive, autoLocalize]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
      }
    } catch (err) {
      console.error("Camera access denied or unavailable", err);
      // Fallback if camera fails (e.g. testing on laptop without webcam)
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
      tracks.forEach((track) => track.stop());
      setCameraActive(false);
    }
  };

  const localizeCurrentCameraFrame = async () => {
    if (isLocalizingRef.current) {
      return;
    }
    const sceneId = selectedDestination?.vpsSceneId || getDefaultSceneId();
    if (!sceneId) {
      setVpsStatus("failed");
      setVpsResult(null);
      setVpsSource("live");
      setVpsError("REACT_APP_SCENE_ID is not configured.");
      return;
    }
    if (!videoRef.current) {
      setVpsStatus("failed");
      setVpsResult(null);
      setVpsSource("live");
      setVpsError("Camera is not ready.");
      return;
    }

    isLocalizingRef.current = true;
    setIsLocalizing(true);
    setVpsStatus("localizing");
    setVpsError(null);
    setVpsSource("live");
    try {
      const result = await localizeVideoFrame({
        video: videoRef.current,
        sceneId,
        agentId: "navigatus-demo-agent",
        apiBaseUrl: getVpsApiBaseUrl(),
      });
      setVpsResult(result);
      setVpsStatus(result.status);
    } catch (err) {
      setVpsStatus("failed");
      setVpsResult(null);
      setVpsError(err instanceof Error ? err.message : "Localization failed.");
    } finally {
      isLocalizingRef.current = false;
      setIsLocalizing(false);
    }
  };

  // --- Recording Functions ---
  const startRecordCamera = useCallback(async () => {
    try {
      const res = RESOLUTION_MAP[recordResolutionRef.current];
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment", width: { ideal: res.width }, height: { ideal: res.height } },
        audio: false,
      });
      recordStreamRef.current = stream;
      if (recordVideoRef.current) {
        recordVideoRef.current.srcObject = stream;
      }
    } catch (err) {
      setRecordingError("Camera access denied or unavailable");
      console.error("Record camera error", err);
    }
  }, []);

  const stopRecordCamera = useCallback(async () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (recordStreamRef.current) {
      recordStreamRef.current.getTracks().forEach((t) => t.stop());
      recordStreamRef.current = null;
    }
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    await new Promise((r) => setTimeout(r, 0));
  }, []);

  const startRecording = useCallback(() => {
    setRecordSettingsOpen(false);
    setCountdownValue(3);
    setRecordingState("countdown");
    setUploadResult(null);
    setRecordingError(null);
  }, []);

  const beginRecording = useCallback(() => {
    const stream = recordStreamRef.current;
    if (!stream) return;

    recordingChunksRef.current = [];
    setRecordingDuration(0);
    setRecordingState("recording");

    const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : MediaRecorder.isTypeSupported("video/webm;codecs=vp8")
      ? "video/webm;codecs=vp8"
      : "video/webm";

    const recorder = new MediaRecorder(stream, { mimeType });
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        recordingChunksRef.current.push(e.data);
      }
    };

    recorder.onstop = () => {
      const blob = new Blob(recordingChunksRef.current, { type: mimeType });
      uploadRecording(blob);
    };

    recorder.start(1000);
    const startTime = Date.now();
    recordingTimerRef.current = window.setInterval(() => {
      setRecordingDuration(Math.floor((Date.now() - startTime) / 1000));
    }, 200);
  }, []);

  // Countdown effect
  useEffect(() => {
    if (recordingState !== "countdown") return;
    if (countdownValue <= 0) {
      beginRecording();
      return;
    }
    const timer = setTimeout(() => setCountdownValue((v) => v - 1), 1000);
    return () => clearTimeout(timer);
  }, [recordingState, countdownValue, beginRecording]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  }, []);

  const uploadRecording = useCallback(async (blob: Blob) => {
    setRecordingState("uploading");
    setUploadProgress(0);

    const formData = new FormData();
    const filename = `navigatus-recording-${Date.now()}.webm`;
    formData.append("file", blob, filename);
    formData.append("name", `Navigatus Mobile Recording ${new Date().toLocaleString()}`);

    const apiBase = getVpsApiBaseUrl();
    const apiKey = process.env.REACT_APP_VPS_API_KEY || "";

    try {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${apiBase}/scene/upload`);

      if (apiKey) {
        xhr.setRequestHeader("X-API-Key", apiKey);
      }

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          setUploadProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      const result = await new Promise<any>((resolve, reject) => {
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            let detail = `Upload failed with HTTP ${xhr.status}`;
            try {
              const payload = JSON.parse(xhr.responseText);
              detail = payload.detail || detail;
            } catch {}
            reject(new Error(detail));
          }
        };
        xhr.onerror = () => reject(new Error("Network error during upload"));
        xhr.send(formData);
      });

      setUploadResult({ id: result.id, name: result.name });
      setRecordingState("done");
      setUploadProgress(100);
    } catch (err) {
      setRecordingError(err instanceof Error ? err.message : "Upload failed");
      setRecordingState("error");
    }
  }, []);

  const formatDuration = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const estimateBitrate = (res: string) => {
    const bitrateMap: Record<string, number> = { "1080p": 8, "720p": 4, "480p": 1.5 };
    return bitrateMap[res] || 4;
  };

  const estimatedFileSize = (res: string, seconds: number) => {
    if (seconds <= 0) return "";
    const mbPerSec = estimateBitrate(res) / 8;
    const total = mbPerSec * seconds;
    if (total >= 1000) return `${(total / 1000).toFixed(1)} GB`;
    return `${Math.round(total)} MB`;
  };

  const localizeDemoFrame = async () => {
    const sceneId = selectedDestination?.vpsSceneId || getDefaultSceneId();
    if (!sceneId) {
      setVpsStatus("failed");
      setVpsResult(null);
      setVpsSource("demo");
      setVpsError("REACT_APP_SCENE_ID is not configured.");
      return;
    }
    if (isLocalizingRef.current) {
      return;
    }

    isLocalizingRef.current = true;
    setAutoLocalize(false);
    setIsLocalizing(true);
    setVpsStatus("localizing");
    setVpsError(null);
    setVpsSource("demo");
    try {
      const result = await localizeDemoQueryImage({
        sceneId,
        agentId: "navigatus-demo-agent",
        apiBaseUrl: getVpsApiBaseUrl(),
        imageUrl: getDemoQueryImageUrl(sceneId),
      });
      setVpsResult(result);
      setVpsStatus(result.status);
    } catch (err) {
      setVpsStatus("failed");
      setVpsResult(null);
      setVpsError(err instanceof Error ? err.message : "Demo localization failed.");
    } finally {
      isLocalizingRef.current = false;
      setIsLocalizing(false);
    }
  };

  const nextArStep = () => {
    if (arStep < arRouteSteps.length - 1) {
      setArStep(arStep + 1);
    } else {
      setCurrentScreen("home");
      setArStep(0);
      setSelectedDestination(null);
    }
  };

  const handleAiSubmit = async () => {
    if (!aiInput.trim()) return;
    setAiLoading(true);
    setAiMessage(null);

    const apiKey = ""; // Disuntik secara automatik dalam persekitaran runtime
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key=${apiKey}`;

    const systemPrompt = `Anda adalah pembantu maya untuk aplikasi hospital NAVIGATUS. 
    Sila baca masalah/simptom pengguna dan pilih ID destinasi yang paling tepat dari senarai berikut:
    1: Farmasi Pesakit Luar (untuk ambil ubat)
    2: Klinik Pakar Bedah (untuk prosedur bedah/surgeri)
    3: Wad Kecemasan / ED (untuk kemalangan, sakit dada akut, sesak nafas, pendarahan, kes kritikal)
    4: Kaunter Hasil / Pembayaran (untuk bayar bil, discaj)
    5: Klinik Ortopedik (untuk tulang patah, sakit sendi, terseliuh, tongkat)
    
    Sila balas dalam format JSON yang tepat dengan dua kunci:
    "destinationId": integer (1-5, atau 0 jika tidak pasti)
    "replyMessage": string (Mesej mesra memberitahu pesakit ke mana mereka perlu pergi dan mengapa. Cth: "Berdasarkan simptom sakit dada, sila segera ke Wad Kecemasan.")`;

    const payload = {
      contents: [{ parts: [{ text: aiInput }] }],
      systemInstruction: { parts: [{ text: systemPrompt }] },
      generationConfig: {
        responseMimeType: "application/json",
        responseSchema: {
          type: "OBJECT",
          properties: {
            destinationId: { type: "INTEGER" },
            replyMessage: { type: "STRING" },
          },
        },
      },
    };

    const fetchWithRetry = async (
      requestUrl: string,
      options: RequestInit,
      retries = 5
    ): Promise<any> => {
      const delays = [1000, 2000, 4000, 8000, 16000];
      for (let i = 0; i < retries; i++) {
        try {
          const response = await fetch(requestUrl, options);
          if (!response.ok)
            throw new Error(`HTTP error! status: ${response.status}`);
          return await response.json();
        } catch (err) {
          if (i === retries - 1) throw err;
          await new Promise((resolve) => setTimeout(resolve, delays[i]));
        }
      }
    };

    try {
      const result = await fetchWithRetry(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const aiText = result.candidates?.[0]?.content?.parts?.[0]?.text;
      if (aiText) {
        const aiResponse = JSON.parse(aiText) as AiDestinationResponse;
        setAiMessage(aiResponse.replyMessage);

        // Tunggu 3 saat untuk pengguna baca nasihat AI sebelum lompat ke peta
        setTimeout(() => {
          const targetDest = destinations.find(
            (d) => d.id === aiResponse.destinationId
          );
          if (targetDest) {
            setSelectedDestination(targetDest);
            setCurrentScreen("route-info");
          } else {
            setAiMessage(
              "Maaf, saya kurang pasti. Sila gunakan carian manual."
            );
            setAiLoading(false);
          }
          setAiLoading(false);
          setAiInput("");
        }, 3500);
      }
    } catch (error) {
      console.error("AI Error:", error);
      setAiMessage("Sistem AI mengalami sedikit gangguan. Sila guna carian.");
      setAiLoading(false);
    }
  };

  // --- KOMPONEN UI ---

  if (currentScreen === "splash") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen hospital-header text-white p-6">
        <div className="animate-pulse flex flex-col items-center">
          <div className="h-24 w-24 rounded-3xl bg-white/15 border border-white/25 flex items-center justify-center mb-5 shadow-clinical">
            <Navigation size={56} />
          </div>
          <h1 className="text-4xl font-extrabold tracking-normal">NAVIGATUS</h1>
          <p className="mt-2 text-white/80 text-center font-medium">
            Smart Hospital Indoor Navigation
          </p>
          <div className="mt-8">
            <div className="w-14 h-14 border-4 border-white/25 border-t-white rounded-full animate-spin"></div>
          </div>
        </div>
        <div className="absolute bottom-10 text-sm text-white/65">
          KIK Inovasi Peringkat UA 2026
        </div>
      </div>
    );
  }

  if (currentScreen === "home") {
    return (
      <div className="mobile-shell flex flex-col relative">
        {/* Header */}
        <div className="hospital-header text-white p-6 rounded-b-[2rem] shadow-clinical">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-white/70">
                NAVIGATUS
              </p>
              <h2 className="text-2xl font-bold mt-1">Hai, Selamat Datang</h2>
            </div>
            <div className="h-12 w-12 rounded-2xl bg-white/15 border border-white/20 flex items-center justify-center">
              <Navigation size={24} />
            </div>
          </div>
          <p className="text-white/80 mt-3">
            Ke mana anda ingin pergi hari ini?
          </p>

          {/* Search Bar */}
          <div className="mt-6 relative">
            <input
              type="text"
              placeholder="Cari wad, klinik, farmasi..."
              className="w-full py-3 pl-12 pr-4 rounded-2xl text-gray-800 focus:outline-none focus:ring-2 focus:ring-white/70 shadow-sm bg-white"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onClick={() => setCurrentScreen("search")}
            />
            <Search
              className="absolute left-4 top-3.5 text-gray-400"
              size={20}
            />
          </div>
        </div>

        {/* Quick Links */}
        <div className="p-6 flex-grow">
          <h3 className="font-bold text-clinical-ink mb-4">Akses Pantas</h3>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => {
                setSelectedDestination(destinations[0]);
                setCurrentScreen("route-info");
              }}
              className="glass-panel p-4 rounded-xl flex flex-col items-center justify-center gap-2 hover:bg-blue-50 transition"
            >
              <div className="bg-green-100 p-3 rounded-full text-green-600">
                <MapIcon size={24} />
              </div>
              <span className="text-sm font-medium text-gray-700 text-center">
                Farmasi
              </span>
            </button>
            <button
              onClick={() => {
                setSelectedDestination(destinations[2]);
                setCurrentScreen("route-info");
              }}
              className="glass-panel p-4 rounded-xl flex flex-col items-center justify-center gap-2 hover:bg-blue-50 transition"
            >
              <div className="bg-red-100 p-3 rounded-full text-red-600">
                <MapPin size={24} />
              </div>
              <span className="text-sm font-medium text-gray-700 text-center">
                Kecemasan
              </span>
            </button>
            <button className="glass-panel p-4 rounded-xl flex flex-col items-center justify-center gap-2 hover:bg-blue-50 transition">
              <div className="bg-purple-100 p-3 rounded-full text-purple-600">
                <Info size={24} />
              </div>
              <span className="text-sm font-medium text-gray-700 text-center">
                Maklumat
              </span>
            </button>
            <button
              onClick={() => setCurrentScreen("record")}
              className="glass-panel p-4 rounded-xl flex flex-col items-center justify-center gap-2 hover:bg-blue-50 transition"
            >
              <div className="bg-red-100 p-3 rounded-full text-red-600">
                <Video size={24} />
              </div>
              <span className="text-sm font-medium text-gray-700 text-center">
                Scene Rec
              </span>
            </button>
          </div>

          {/* AI Feature Banner */}
          <div className="mt-6">
            <button
              onClick={() => {
                setAiMessage(null);
                setAiInput("");
                setCurrentScreen("ai-assistant");
              }}
              className="w-full bg-clinical-ink rounded-xl p-4 shadow-clinical text-white flex items-center justify-between active:scale-95 transition-all"
            >
              <div className="flex items-center gap-4">
                <div className="bg-white/20 p-3 rounded-full">
                  <Sparkles size={24} className="text-yellow-300" />
                </div>
                <div className="text-left">
                  <h4 className="font-bold text-lg">Tanya AI Pintar ✨</h4>
                  <p className="text-sm text-indigo-100">
                    Bantu pilih arah berdasarkan simptom
                  </p>
                </div>
              </div>
              <ArrowRight size={20} className="text-white/70" />
            </button>
          </div>

          {/* Banner Promo / Info */}
          <div className="mt-4 bg-clinical-mint rounded-xl p-4 border border-teal-100 flex items-start gap-4">
            <div className="bg-clinical-teal text-white p-2 rounded-lg">
              <Camera size={20} />
            </div>
            <div>
              <h4 className="font-bold text-clinical-ink text-sm">
                AR Navigasi Kini Tersedia!
              </h4>
              <p className="text-xs text-teal-700 mt-1">
                Gunakan kamera anda untuk panduan arah maya yang lebih tepat.
                (Beta)
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (currentScreen === "ai-assistant") {
    return (
      <div className="mobile-shell flex flex-col relative bg-clinical-surface">
        <div className="hospital-header text-white p-6 rounded-b-[2rem] shadow-clinical flex items-center gap-3">
          <button
            onClick={() => setCurrentScreen("home")}
            className="p-2 bg-white/20 rounded-full hover:bg-white/30 transition"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Sparkles size={18} className="text-yellow-300" /> AI NAVIGATUS
            </h2>
          </div>
        </div>

        <div className="flex-grow p-6 flex flex-col justify-center">
          <div className="glass-panel rounded-xl p-6 text-center">
            <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4 border-4 border-white shadow-sm">
              <Bot size={40} className="text-indigo-600" />
            </div>

            {!aiMessage && !aiLoading ? (
              <>
                <h3 className="text-xl font-bold text-gray-800 mb-2">
                  Bagaimana saya boleh bantu?
                </h3>
                <p className="text-gray-500 text-sm mb-6">
                  Nyatakan simptom atau tujuan anda. Saya akan fahami masalah
                  anda dan padankan dengan lokasi yang tepat di hospital.
                </p>
              </>
            ) : (
              <div className="min-h-[140px] flex flex-col items-center justify-center">
                {aiLoading && !aiMessage && (
                  <div className="flex flex-col items-center">
                    <Loader2
                      size={32}
                      className="text-indigo-600 animate-spin mb-4"
                    />
                    <p className="text-sm text-gray-500">
                      Menganalisis permintaan anda...
                    </p>
                  </div>
                )}
                {aiMessage && (
                  <div className="bg-indigo-50 p-4 rounded-xl text-indigo-800 font-medium border border-indigo-100 animate-pulse text-sm">
                    "{aiMessage}"
                  </div>
                )}
                {aiMessage && (
                  <p className="text-xs text-gray-400 mt-4">
                    Mencari laluan ke destinasi...
                  </p>
                )}
              </div>
            )}

            <div className="relative mt-4">
              <textarea
                placeholder="Contoh: Saya patah tangan waktu main bola tadi..."
                className="w-full bg-gray-50 border border-gray-200 rounded-xl p-4 pr-12 focus:outline-none focus:ring-2 focus:ring-indigo-400 focus:border-transparent resize-none h-28 text-gray-800"
                value={aiInput}
                onChange={(e) => setAiInput(e.target.value)}
                disabled={aiLoading}
              />
              <button
                onClick={handleAiSubmit}
                disabled={aiLoading || !aiInput.trim()}
                className="absolute bottom-4 right-4 p-3 bg-indigo-600 text-white rounded-lg disabled:opacity-50 disabled:bg-gray-400 hover:bg-indigo-700 transition"
              >
                <MessageSquare size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (currentScreen === "search") {
    const filteredResults = destinations.filter((d) =>
      d.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return (
      <div className="mobile-shell flex flex-col">
        <div className="bg-white p-4 flex items-center gap-3 border-b border-gray-200">
          <button
            onClick={() => setCurrentScreen("home")}
            className="p-2 bg-gray-100 rounded-full hover:bg-gray-200"
          >
            <ArrowLeft size={20} className="text-gray-600" />
          </button>
          <div className="relative flex-grow">
            <input
              type="text"
              autoFocus
              placeholder="Cari..."
              className="w-full py-2 pl-10 pr-4 bg-gray-100 rounded-lg text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Search
              className="absolute left-3 top-2.5 text-gray-400"
              size={18}
            />
          </div>
        </div>

        <div className="p-3 flex-grow overflow-y-auto">
          {filteredResults.length > 0 ? (
            filteredResults.map((dest) => (
              <div
                key={dest.id}
                className="glass-panel p-4 mb-3 rounded-xl flex justify-between items-center cursor-pointer hover:bg-blue-50"
                onClick={() => {
                  setSelectedDestination(dest);
                  setCurrentScreen("route-info");
                }}
              >
                <div>
                  <h3 className="font-semibold text-gray-800">{dest.name}</h3>
                  <p className="text-xs text-gray-500">{dest.department}</p>
                </div>
                <div className="text-right">
                  <span className="text-sm font-bold text-blue-600">
                    {dest.distance}
                  </span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center p-10 text-gray-500">
              <p>Tiada padanan ditemui.</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (currentScreen === "route-info" && selectedDestination) {
    return (
      <div className="mobile-shell flex flex-col">
        {/* Placeholder Map View */}
        <div className="h-64 wayfinding-map relative flex items-center justify-center overflow-hidden">
          {/* Simulate a map background using a subtle pattern/gradient */}
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-100 via-gray-200 to-gray-300"></div>

          {/* Map Path Simulation Graphic */}
          <div className="relative z-10 w-full h-full p-8 flex flex-col items-center justify-between">
            <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center text-white shadow-lg border-4 border-white animate-pulse">
              <MapPin size={24} />
            </div>
            <div className="h-full w-2 border-l-4 border-dashed border-blue-500"></div>
            <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center text-white shadow-lg border-4 border-white">
              <MapPin size={24} />
            </div>
          </div>

          <button
            onClick={() => setCurrentScreen("search")}
            className="absolute top-4 left-4 p-2 bg-white rounded-full shadow-md z-20"
          >
            <ArrowLeft size={20} className="text-gray-800" />
          </button>
        </div>

        {/* Route Details */}
        <div className="bg-white rounded-t-[2rem] -mt-6 p-6 flex-grow z-20 shadow-[0_-10px_40px_rgba(16,32,51,0.14)] relative">
          <div className="w-12 h-1.5 bg-gray-300 rounded-full mx-auto mb-6"></div>

          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-800">
                {selectedDestination.name}
              </h2>
              <p className="text-gray-500 mt-1">
                {selectedDestination.department}
              </p>
            </div>
          </div>

          <div className="flex gap-4 mb-8">
            <div className="flex-1 bg-gray-50 rounded-xl p-4 border border-gray-100 text-center">
              <div className="text-sm text-gray-500 mb-1">Jarak</div>
              <div className="text-xl font-bold text-blue-600">
                {selectedDestination.distance}
              </div>
            </div>
            <div className="flex-1 bg-gray-50 rounded-xl p-4 border border-gray-100 text-center">
              <div className="text-sm text-gray-500 mb-1">Masa</div>
              <div className="text-xl font-bold text-blue-600">
                {selectedDestination.estTime}
              </div>
            </div>
          </div>

          <div className="mb-6 rounded-xl border border-clinical-line bg-clinical-surface p-4">
            <div className="flex items-start gap-3">
              <DatabaseIcon />
              <div className="min-w-0">
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500">
                  VPS Scene Binding
                </p>
                <p className="mt-1 text-sm font-bold text-clinical-ink">
                  {selectedDestination.vpsSceneLabel || "No VPS scene assigned"}
                </p>
                <p className="mt-1 break-all font-mono text-[11px] text-gray-500">
                  {selectedDestination.vpsSceneId || "Set REACT_APP_SCENE_ID in navigatus/.env"}
                </p>
              </div>
            </div>
          </div>

          <button
            onClick={() => setCurrentScreen("ar-view")}
            className="w-full bg-clinical-blue text-white font-bold text-lg py-4 rounded-xl shadow-clinical flex items-center justify-center gap-2 hover:bg-blue-700 active:scale-95 transition-all"
          >
            <Camera size={24} />
            Mula Navigasi AR
          </button>

          <button
            onClick={() => setCurrentScreen("home")}
            className="w-full bg-transparent text-gray-500 font-semibold py-4 mt-2"
          >
            Batal
          </button>
        </div>
      </div>
    );
  }

  if (currentScreen === "ar-view") {
    const currentInstruction = arRouteSteps[arStep];
    const statusStyle =
      vpsStatus === "locked"
        ? "bg-green-500"
        : vpsStatus === "weak"
        ? "bg-amber-500"
        : vpsStatus === "localizing"
        ? "bg-blue-500"
        : vpsStatus === "failed"
        ? "bg-red-500"
        : "bg-gray-500";
    const statusLabel =
      vpsStatus === "locked"
        ? "VPS LOCKED"
        : vpsStatus === "weak"
        ? "WEAK SIGNAL"
        : vpsStatus === "localizing"
        ? "LOCALIZING"
        : vpsStatus === "failed"
        ? "VPS FAILED"
        : "VPS IDLE";

    return (
      <div className="flex flex-col min-h-screen bg-black max-w-md mx-auto shadow-xl relative overflow-hidden">
        {/* Camera Feed Background */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover opacity-80"
        />

        {/* Fallback pattern if camera fails */}
        {!cameraActive && (
          <div className="absolute inset-0 w-full h-full bg-gray-900 flex items-center justify-center">
            <p className="text-gray-500 text-sm">Simulasi Kamera...</p>
          </div>
        )}

        {/* Top Header Overlay */}
        <div className="absolute top-0 w-full p-6 bg-gradient-to-b from-black/70 to-transparent z-10 flex justify-between items-center">
          <button
            onClick={() => setCurrentScreen("route-info")}
            className="p-2 bg-white/20 backdrop-blur-md rounded-full text-white"
          >
            <X size={24} />
          </button>
          <div className="bg-blue-600 text-white px-4 py-1.5 rounded-full text-sm font-bold shadow-md flex items-center gap-2">
            <MapPin size={16} /> {selectedDestination?.name}
          </div>
        </div>

        <div className="absolute top-20 left-4 right-4 z-20 bg-black/60 backdrop-blur-md rounded-2xl border border-white/20 p-3 text-white">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className={`h-2.5 w-2.5 rounded-full ${statusStyle}`} />
                <span className="text-xs font-bold tracking-wide">{statusLabel}</span>
              </div>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-wide text-white/45">
                Source:{" "}
                {vpsSource === "demo"
                  ? "Demo Query Frame"
                  : vpsSource === "live"
                  ? "Live Camera"
                  : "Not localized"}
              </p>
              {vpsResult ? (
                <p className="mt-1 text-[11px] text-white/70 truncate">
                  Conf {(vpsResult.pose.confidence * 100).toFixed(0)}% · {vpsResult.pose.inliers} inliers · XYZ{" "}
                  {vpsResult.pose.position.map((v) => v.toFixed(2)).join(", ")}
                </p>
              ) : (
                <p className="mt-1 text-[11px] text-white/70">
                  {vpsError || "Capture a frame to align this route with the VPS map."}
                </p>
              )}
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                localizeCurrentCameraFrame();
              }}
              disabled={isLocalizing || !cameraActive}
              className="shrink-0 bg-white text-gray-900 px-3 py-2 rounded-xl text-xs font-bold disabled:opacity-50"
            >
              {isLocalizing ? "..." : "Relocalize"}
            </button>
          </div>
          <div className="mt-3 flex items-center justify-between gap-3 border-t border-white/10 pt-3">
            <span className="text-[11px] text-white/60">
              Auto VPS every 4s
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  localizeDemoFrame();
                }}
                disabled={isLocalizing}
                className="rounded-full bg-white/15 px-3 py-1 text-[11px] font-bold text-white disabled:opacity-50"
              >
                Demo Frame
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setAutoLocalize((value) => !value);
                }}
                className={`rounded-full px-3 py-1 text-[11px] font-bold ${
                  autoLocalize ? "bg-green-500 text-white" : "bg-white/15 text-white/70"
                }`}
              >
                {autoLocalize ? "ON" : "OFF"}
              </button>
            </div>
          </div>
        </div>

        {/* AR Directional Overlay (Wizard of Oz click target) */}
        {/* WIZARD OF OZ TRICK: Tapping anywhere on the screen advances the instruction! */}
        <div
          className="relative z-10 flex-grow flex flex-col items-center justify-center w-full cursor-pointer"
          onClick={nextArStep}
        >
          {/* Floating AR Arrow Simulation */}
          <div
            className={`transition-all duration-500 transform ${
              arStep % 2 === 0 ? "translate-y-0" : "-translate-y-4"
            }`}
          >
            {currentInstruction.icon}
          </div>

          <div className="mt-8 bg-black/60 backdrop-blur-md text-white px-6 py-3 rounded-2xl border border-white/20 text-center animate-pulse">
            Tekan skrin untuk simulasi langkah seterusnya
          </div>
        </div>

        {/* Bottom Instruction Panel */}
        <div className="absolute bottom-0 w-full bg-white rounded-t-3xl p-6 z-20 shadow-[0_-10px_40px_rgba(0,0,0,0.3)]">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-gray-500 text-sm font-semibold uppercase tracking-wider mb-1">
                Arahan Semasa
              </p>
              <h2 className="text-2xl font-bold text-gray-900 leading-tight">
                {currentInstruction.text}
              </h2>
            </div>
            <div className="bg-blue-100 text-blue-700 w-16 h-16 rounded-full flex flex-col items-center justify-center font-bold shadow-inner">
              <span className="text-xl leading-none">
                {currentInstruction.distance.replace("m", "")}
              </span>
              <span className="text-xs">meter</span>
            </div>
          </div>

          {/* Progress Indicator */}
          <div className="mt-6 flex gap-1">
            {arRouteSteps.map((_, idx) => (
              <div
                key={idx}
                className={`h-1.5 flex-1 rounded-full ${
                  idx <= arStep ? "bg-blue-600" : "bg-gray-200"
                }`}
              ></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (currentScreen === "record") {
    const pulse = recordingState === "recording" ? "animate-pulse" : "";
    const currentRes = RESOLUTION_MAP[recordResolution];
    const currentBitrate = estimateBitrate(recordResolution);

    return (
      <div className="flex flex-col min-h-screen bg-black max-w-md mx-auto shadow-xl relative overflow-hidden">
        {/* Camera Preview */}
        <video
          ref={recordVideoRef}
          autoPlay
          playsInline
          muted
          className="absolute inset-0 w-full h-full object-cover opacity-80"
        />

        {!recordStreamRef.current && !recordingError && (
          <div className="absolute inset-0 bg-gray-900 flex items-center justify-center">
            <Camera size={48} className="text-gray-600" />
          </div>
        )}

        {/* Header */}
        <div className="absolute top-0 w-full p-6 bg-gradient-to-b from-black/70 to-transparent z-10 flex justify-between items-center">
          <button
            onClick={() => {
              stopRecordCamera();
              setRecordingState("idle");
              setRecordingDuration(0);
              setCountdownValue(3);
              setUploadResult(null);
              setRecordingError(null);
              setRecordSettingsOpen(false);
              setCurrentScreen("home");
            }}
            className="p-2 bg-white/20 backdrop-blur-md rounded-full text-white"
          >
            <X size={24} />
          </button>
          <div className="bg-red-600 text-white px-4 py-1.5 rounded-full text-sm font-bold shadow-md flex items-center gap-2">
            <Video size={16} /> Scene Recording
          </div>
          {recordingState === "idle" && (
            <button
              onClick={() => setRecordSettingsOpen((v) => !v)}
              className="p-2 bg-white/20 backdrop-blur-md rounded-full text-white"
            >
              <Settings2 size={20} />
            </button>
          )}
          {recordingState !== "idle" && <div className="w-10" />}
        </div>

        {/* Settings panel */}
        {recordSettingsOpen && recordingState === "idle" && (
          <div className="absolute top-20 right-4 z-30 bg-gray-900/95 backdrop-blur-xl rounded-2xl border border-white/20 p-4 text-white min-w-[200px] shadow-2xl">
            <p className="text-xs font-bold uppercase tracking-wider text-white/50 mb-3">Resolution</p>
            <div className="space-y-1">
              {(["1080p", "720p", "480p"] as const).map((res) => {
                const info = RESOLUTION_MAP[res];
                return (
                  <button
                    key={res}
                    onClick={async () => {
                      setRecordResolution(res);
                      await stopRecordCamera();
                      await startRecordCamera();
                    }}
                    className={`w-full text-left px-3 py-2 rounded-xl text-sm font-medium transition ${
                      recordResolution === res
                        ? "bg-blue-600 text-white"
                        : "text-white/70 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span>{info.label}</span>
                      {recordResolution === res && <Check size={14} className="text-white" />}
                    </div>
                  </button>
                );
              })}
            </div>
            <div className="mt-3 pt-3 border-t border-white/10">
              <p className="text-[10px] text-white/40">
                Est. bitrate: {currentBitrate} Mbps
              </p>
            </div>
          </div>
        )}

        {/* Countdown Overlay */}
        {recordingState === "countdown" && (
          <div className="absolute inset-0 z-20 bg-black/70 flex items-center justify-center">
            <div className="text-center">
              <div className="text-8xl font-black text-white drop-shadow-2xl animate-ping">
                {countdownValue}
              </div>
              <p className="text-white/50 text-sm mt-4 font-medium">Get ready...</p>
            </div>
          </div>
        )}

        {/* Status overlay */}
        <div className="absolute top-20 left-4 right-4 z-20 bg-black/60 backdrop-blur-md rounded-2xl border border-white/20 p-4 text-white">
          {recordingState === "idle" && !recordSettingsOpen && (
            <div className="text-center">
              <p className="text-sm text-white/80">
                Press the button to record a video for VPS mapping.
              </p>
              <p className="text-[10px] text-white/40 mt-1">
                {currentRes.label} · ~{currentBitrate} Mbps
              </p>
            </div>
          )}

          {recordingState === "recording" && (
            <div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`h-3 w-3 rounded-full bg-red-500 ${pulse}`} />
                  <span className="text-sm font-bold">REC</span>
                </div>
                <span className="text-2xl font-mono font-bold tabular-nums">
                  {formatDuration(recordingDuration)}
                </span>
              </div>
              {/* Recording activity bars (CSS-animated) */}
              <div className="mt-3 flex items-center gap-0.5 h-6">
                {Array.from({ length: 20 }).map((_, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-red-500/40 rounded-full animate-pulse"
                    style={{
                      height: `${30 + (i % 5) * 14}%`,
                      animationDelay: `${i * 0.1}s`,
                      animationDuration: `${0.4 + (i % 3) * 0.2}s`,
                    }}
                  />
                ))}
              </div>
              <div className="mt-2 flex justify-between text-[10px] text-white/40">
                <span>{currentRes.label}</span>
                <span>~{estimatedFileSize(recordResolution, recordingDuration)}</span>
              </div>
            </div>
          )}

          {recordingState === "uploading" && (
            <div className="text-center">
              <p className="text-sm font-bold mb-2">Uploading recording...</p>
              <div className="w-full bg-white/20 rounded-full h-2">
                <div
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
              <p className="text-xs text-white/60 mt-1">{uploadProgress}%</p>
            </div>
          )}

          {recordingState === "done" && uploadResult && (
            <div className="text-center">
              <div className="flex items-center justify-center gap-2 text-green-400">
                <Check size={20} />
                <span className="text-sm font-bold">Upload complete!</span>
              </div>
              <p className="text-xs text-white/60 mt-1 break-all">{uploadResult.name}</p>
              <p className="text-[10px] text-white/40 mt-0.5 font-mono">{uploadResult.id}</p>
            </div>
          )}

          {recordingState === "error" && (
            <div className="text-center">
              <div className="flex items-center justify-center gap-2 text-red-400">
                <AlertCircle size={20} />
                <span className="text-sm font-bold">Upload failed</span>
              </div>
              <p className="text-xs text-white/60 mt-1">{recordingError}</p>
            </div>
          )}
        </div>

        {/* Bottom Controls */}
        <div className="absolute bottom-0 w-full bg-gradient-to-t from-black/80 to-transparent p-8 z-20 flex flex-col items-center gap-4">
          {/* Recording button */}
          {recordingState === "idle" && (
            <button
              onClick={startRecording}
              disabled={!recordStreamRef.current}
              className="h-16 w-16 rounded-full bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed flex items-center justify-center transition shadow-lg active:scale-90"
            >
              <div className="h-8 w-8 rounded-full border-4 border-white" />
            </button>
          )}

          {recordingState === "countdown" && (
            <div className="h-16 w-16 rounded-full bg-red-600/50 flex items-center justify-center">
              <div className="h-8 w-8 rounded-full border-4 border-white/50" />
            </div>
          )}

          {recordingState === "recording" && (
            <button
              onClick={stopRecording}
              className="h-16 w-16 rounded-full bg-red-600 hover:bg-red-700 flex items-center justify-center transition shadow-lg active:scale-90"
            >
              <Square size={24} className="text-white" />
            </button>
          )}

          {recordingState === "uploading" && (
            <div className="flex items-center gap-2 text-white/60">
              <Upload size={20} className="animate-bounce" />
              <span className="text-sm">Uploading...</span>
            </div>
          )}

          {(recordingState === "done" || recordingState === "error") && (
            <button
              onClick={() => {
                setRecordingState("idle");
                setRecordingDuration(0);
                setCountdownValue(3);
                setUploadResult(null);
                setRecordingError(null);
              }}
              className="bg-white text-gray-900 px-6 py-3 rounded-xl font-bold shadow-lg hover:bg-gray-100 transition active:scale-95"
            >
              Record Another
            </button>
          )}

          {/* Hint text */}
          {recordingState === "idle" && recordStreamRef.current && !recordSettingsOpen && (
            <p className="text-white/50 text-xs text-center max-w-[280px]">
              Point your camera at the area you want to map. Move slowly and cover all angles for best results.
            </p>
          )}
        </div>
      </div>
    );
  }

  return null;
}

function DatabaseIcon() {
  return (
    <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-clinical-blue shadow-sm">
      <MapIcon size={18} />
    </div>
  );
}
