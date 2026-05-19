import { useState } from "react";
import { ChevronDown, User } from "lucide-react";
import PaperUpload from "./components/PaperUpload";
import TranslatorPanel from "./components/TranslatorPanel";
import LoginModal from "./components/LoginModal";
import PersonaModal from "./components/PersonaModal";
import ProfilePage from "./components/ProfilePage";
import { useAuth } from "./contexts/AuthContext";

type View = "translate" | "profile";

function App() {
  const [uploadOpen, setUploadOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [personaOpen, setPersonaOpen] = useState(false);
  const [view, setView] = useState<View>("translate");
  const { user, me, signOut, loading: authLoading } = useAuth();

  const displayName = me?.username || me?.persona?.username || user?.email?.split("@")[0] || "";

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-blue-50/30">
      {/* Header */}
      <header className="border-b border-slate-200/80 bg-white/70 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/favicon.png" alt="GAIA Lab" className="w-9 h-9 rounded-lg shadow-sm" />
            <div>
              <h1 className="text-lg font-bold text-slate-800 tracking-tight">
                GAIA Translator
              </h1>
              <p className="text-[11px] text-slate-400 -mt-0.5">
                Interdisciplinary Geohazard Knowledge Bridge
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {!authLoading && (
              <>
                {user ? (
                  <>
                    {/* Tab switcher */}
                    <div className="hidden sm:flex items-center rounded-lg border border-slate-200 p-0.5 mr-1">
                      <button
                        onClick={() => setView("translate")}
                        className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                          view === "translate"
                            ? "bg-slate-800 text-white"
                            : "text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        Translate
                      </button>
                      <button
                        onClick={() => setView("profile")}
                        className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors ${
                          view === "profile"
                            ? "bg-slate-800 text-white"
                            : "text-slate-600 hover:bg-slate-50"
                        }`}
                      >
                        Profile
                      </button>
                    </div>
                    {/* User pill — opens the quick modal */}
                    <button
                      onClick={() => setView("profile")}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                                 text-slate-700 border border-slate-200 rounded-lg hover:bg-slate-50
                                 transition-colors"
                      title="Open profile"
                    >
                      <User className="w-3.5 h-3.5 text-slate-400" />
                      {displayName || "My profile"}
                    </button>
                    <button
                      onClick={() => signOut()}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                                 text-slate-500 border border-slate-200 rounded-lg hover:bg-slate-50
                                 transition-colors"
                    >
                      Log out
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setLoginOpen(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                               text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50
                               transition-colors"
                  >
                    Log in / Sign up
                  </button>
                )}
                <button
                  onClick={() => setUploadOpen((v) => !v)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium
                             text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50
                             transition-colors"
                >
                  Add paper
                  <ChevronDown
                    className={`w-3.5 h-3.5 transition-transform ${uploadOpen ? "rotate-180" : ""}`}
                  />
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <LoginModal open={loginOpen} onClose={() => setLoginOpen(false)} />
      <PersonaModal open={personaOpen} onClose={() => setPersonaOpen(false)} />

      {/* Upload panel */}
      {uploadOpen && (
        <div className="max-w-6xl mx-auto px-6 pt-4">
          <PaperUpload />
        </div>
      )}

      {/* Persona prompt for new users */}
      {user && me && !me.persona?.bio && !personaOpen && (
        <div className="max-w-6xl mx-auto px-6 pt-4">
          <button
            onClick={() => setPersonaOpen(true)}
            className="w-full text-left rounded-lg border border-blue-100 bg-blue-50/60 px-4 py-3
                       text-xs text-blue-700 hover:bg-blue-50 transition-colors"
          >
            <span className="font-medium">Set up your profile</span> — add a bio and specialization
            tags so translations are tailored to your background.{" "}
            <span className="underline">Set up now →</span>
          </button>
        </div>
      )}

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-6 py-8">
        {view === "profile" && user ? (
          <ProfilePage onClose={() => setView("translate")} />
        ) : (
          <TranslatorPanel />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200/60 mt-12">
        <div className="max-w-6xl mx-auto px-6 py-4 text-center">
          <p className="text-[11px] text-slate-400">
            GAIA — Bridging soil understanding across hydrology, seismology, atmospheric science,
            climatology, geology, computer science, and applied mathematics
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
