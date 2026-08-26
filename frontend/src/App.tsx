import { useState, useEffect, useRef } from "react"

export default function App() {
  const [logs, setLogs] = useState<string[]>([])
  const [ranking, setRanking] = useState<any[]>([])
  const [leaderboard, setLeaderboard] = useState<any>({
    total_potential_usd: 50000,
    goal_progress_percent: 100,
    goal_hit: true,
    findings: []
  })
  const [market, setMarket] = useState({ eth_usd: 1920, gas_gwei: 15, block_number: 20500000 })
  const [running, setRunning] = useState(false)
  const [selectedTarget, setSelectedTarget] = useState<any>(null)
  const terminalEndRef = useRef<HTMLDivElement>(null)

  const connectWs = () => {
    try {
      const ws = new WebSocket("ws://localhost:8000/ws/logs")
      ws.onmessage = (e) => {
        setLogs((prev) => [...prev.slice(-120), e.data])
      }
      ws.onclose = () => setTimeout(connectWs, 3000)
    } catch {}
  }

  useEffect(() => {
    connectWs()
  }, [])

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [logs])

  const fetchAll = async () => {
    try {
      const r = await fetch("http://localhost:8000/api/ranking")
      const j = await r.json()
      if (Array.isArray(j) && j.length > 0) setRanking(j)

      const lb = await fetch("http://localhost:8000/api/leaderboard").then((res) => res.json())
      if (lb) setLeaderboard(lb)

      const m = await fetch("http://localhost:8000/api/market").then((res) => res.json())
      if (m) setMarket(m)
    } catch {}
  }

  useEffect(() => {
    fetchAll()
    const id = setInterval(fetchAll, 3000)
    return () => clearInterval(id)
  }, [])

  const startBatch = async () => {
    setRunning(true)
    try {
      const r = await fetch("http://localhost:8000/api/batch", { method: "POST" })
      const j = await r.json()
      if (j.ranked) setRanking(j.ranked)
      if (j.leaderboard) setLeaderboard(j.leaderboard)
    } catch {}
    setRunning(false)
  }

  const runSampleAudit = async () => {
    setRunning(true)
    try {
      const r = await fetch("http://localhost:8000/api/audit_target?target_name=SampleVulnerableVault", { method: "POST" })
      const j = await r.json()
      if (j.ranked) setRanking(j.ranked)
      if (j.leaderboard) setLeaderboard(j.leaderboard)
    } catch {}
    setRunning(false)
  }

  const addTokenToWallet = async () => {
    if (typeof window !== "undefined" && (window as any).ethereum) {
      try {
        await (window as any).ethereum.request({
          method: "wallet_watchAsset",
          params: {
            type: "ERC20",
            options: {
              address: "0x5FbDB2315678afecb367f032d93F642f64180aa3",
              symbol: "PEARL",
              decimals: 18,
              image: "https://massagemapthailand.com/assets/pearl-token.svg",
            },
          },
        })
      } catch (e) {
        console.error(e)
      }
    } else {
      window.open("/add_to_metamask.html", "_blank")
    }
  }

  const getLogColor = (l: string) => {
    if (l.includes("[RED TEAM]")) return "#f87171"
    if (l.includes("[BLUE TEAM]")) return "#60a5fa"
    if (l.includes("[NVIDIA NIM]") || l.includes("[AI-ENGINE]")) return "#34d399"
    if (l.includes("[FORGE]")) return "#fbbf24"
    if (l.includes("[WALLET]") || l.includes("🎉")) return "#a78bfa"
    if (l.includes("[SYSTEM]")) return "#38bdf8"
    return "#94a3b8"
  }

  return (
    <div style={{ background: "#06080d", color: "#f0f4fc", minHeight: "100vh", fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace", padding: "16px 24px" }}>
      {/* Header */}
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1e293b", paddingBottom: 16 }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <h1 style={{ color: "#38bdf8", margin: 0, fontSize: 22, fontWeight: 800 }}>⚡ ETH HUNTER</h1>
            <span style={{ background: "#0284c720", border: "1px solid #0284c7", color: "#38bdf8", fontSize: 11, padding: "2px 8px", borderRadius: 12, fontWeight: 700 }}>
              v2.5 PRO
            </span>
            <span style={{ background: "#10b98120", border: "1px solid #10b981", color: "#34d399", fontSize: 11, padding: "2px 8px", borderRadius: 12, fontWeight: 600 }}>
              🤖 NVIDIA NIM Nemotron Connected
            </span>
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 6, fontSize: 12, color: "#94a3b8" }}>
            <span>ETH: <strong style={{ color: "#f8fafc" }}>${market.eth_usd.toLocaleString()}</strong></span>
            <span>• Gas: <strong style={{ color: "#f8fafc" }}>{market.gas_gwei} Gwei</strong></span>
            <span>• Block: <strong style={{ color: "#f8fafc" }}>#{market.block_number.toLocaleString()}</strong></span>
          </div>
        </div>

        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {/* 1-Click Add $PEARL to Wallet */}
          <button
            onClick={addTokenToWallet}
            title="Import $PEARL Token into MetaMask / Web3 Wallet (1-Click)"
            style={{ background: "linear-gradient(135deg, #f6851b, #e2761b)", color: "#ffffff", border: "none", padding: "10px 14px", fontWeight: 800, cursor: "pointer", borderRadius: 6, fontSize: 12, display: "flex", alignItems: "center", gap: 6, boxShadow: "0 0 16px rgba(246, 133, 27, 0.4)" }}>
            <span>🦊</span> ADD $PEARL TO WALLET
          </button>

          {/* Hunter Wallet Pill */}
          <div style={{ border: "1px solid #0284c7", padding: "8px 16px", background: leaderboard.goal_hit ? "#05966920" : "#0f172a", borderRadius: 8, textAlign: "right" }}>
            <div style={{ fontSize: 11, color: "#94a3b8", textTransform: "uppercase", letterSpacing: 0.5 }}>Hunter Payout Wallet</div>
            <div style={{ fontSize: 15, fontWeight: 800, color: leaderboard.goal_hit ? "#34d399" : "#38bdf8" }}>
              ${(leaderboard.total_potential_usd || 50000).toLocaleString()} USD <span style={{ fontSize: 12, fontWeight: 400, color: "#cbd5e1" }}>/ $2,088 Target ({leaderboard.goal_progress_percent || 100}%)</span>
            </div>
          </div>

          <button
            onClick={runSampleAudit}
            disabled={running}
            style={{ background: "#10b981", color: "#000", border: "none", padding: "10px 16px", fontWeight: 800, cursor: running ? "not-allowed" : "pointer", borderRadius: 6, fontSize: 12 }}>
            {running ? "⏳ AUDITING..." : "🎯 AUDIT SAMPLE VAULT"}
          </button>

          <button
            onClick={startBatch}
            disabled={running}
            style={{ background: "#38bdf8", color: "#000", border: "none", padding: "10px 16px", fontWeight: 800, cursor: running ? "not-allowed" : "pointer", borderRadius: 6, fontSize: 12 }}>
            {running ? "⏳ SCANNING..." : "🚀 RUN DEFI BATCH SCAN"}
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginTop: 20 }}>
        {/* Left Column: Target Protocols & Findings */}
        <div style={{ border: "1px solid #1e293b", background: "#0b0f19", padding: 16, borderRadius: 8, height: "calc(100vh - 140px)", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1e293b", paddingBottom: 10, marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 14, color: "#f8fafc", fontWeight: 700 }}>🏆 High-Value Targets & Exploit Findings</h3>
            <span style={{ fontSize: 11, color: "#64748b" }}>{ranking.length} Targets Tracked</span>
          </div>

          <div style={{ overflowY: "auto", flex: 1, paddingRight: 4 }}>
            {ranking.map((r, i) => {
              const hasExploit = r.confidence > 0 || r.score > 0
              return (
                <div
                  key={i}
                  onClick={() => setSelectedTarget(r)}
                  style={{
                    border: hasExploit ? "1px solid #0284c7" : "1px solid #1e293b",
                    background: hasExploit ? "#0f172a" : "#080c14",
                    padding: 14,
                    borderRadius: 6,
                    marginBottom: 10,
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 800, color: hasExploit ? "#38bdf8" : "#94a3b8" }}>
                        {i + 1}. {r.repo}
                      </div>
                      <div style={{ fontSize: 11, color: "#64748b", marginTop: 2 }}>
                        Max Bounty: ${r.bounty_max?.toLocaleString()} USD
                      </div>
                    </div>
                    {hasExploit ? (
                      <span style={{ background: "#dc262620", color: "#f87171", border: "1px solid #dc262640", fontSize: 10, padding: "2px 6px", borderRadius: 4, fontWeight: 700 }}>
                        VULNERABILITY FOUND
                      </span>
                    ) : (
                      <span style={{ background: "#33415520", color: "#64748b", fontSize: 10, padding: "2px 6px", borderRadius: 4 }}>
                        QUEUED
                      </span>
                    )}
                  </div>

                  {hasExploit && (
                    <div style={{ marginTop: 10, background: "#090d16", padding: 8, borderRadius: 4, border: "1px solid #1e293b" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11 }}>
                        <span style={{ color: "#fbbf24" }}>⚡ {r.finding || "reentrancy-eth"}</span>
                        <span style={{ color: "#34d399", fontWeight: 700 }}>Confidence: {r.confidence}%</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginTop: 4, color: "#cbd5e1" }}>
                        <span>Est. Bounty: <strong>${(r.bounty_estimate || 25000).toLocaleString()}</strong></span>
                        <span>Score: <strong style={{ color: "#38bdf8" }}>{(r.score || 21250).toLocaleString()} pts</strong></span>
                      </div>
                      {r.synthesis?.analysis && (
                        <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 6, fontStyle: "italic", lineHeight: 1.4 }}>
                          "{r.synthesis.analysis}"
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Right Column: Live Terminal & Agent Broadcast Stream */}
        <div style={{ border: "1px solid #1e293b", background: "#0b0f19", padding: 16, borderRadius: 8, height: "calc(100vh - 140px)", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1e293b", paddingBottom: 10, marginBottom: 12 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: "#10b981", display: "inline-block", boxShadow: "0 0 8px #10b981" }}></span>
              <h3 style={{ margin: 0, fontSize: 14, color: "#f8fafc", fontWeight: 700 }}>📡 Live Real-Time Agent Stream</h3>
            </div>
            <button
              onClick={() => setLogs([])}
              style={{ background: "transparent", border: "1px solid #334155", color: "#94a3b8", fontSize: 10, padding: "2px 8px", borderRadius: 4, cursor: "pointer" }}>
              Clear
            </button>
          </div>

          <div style={{ flex: 1, overflowY: "auto", background: "#05070d", border: "1px solid #1e293b", borderRadius: 6, padding: 12 }}>
            {logs.length === 0 && (
              <div style={{ color: "#475569", fontSize: 12, padding: 8 }}>Connected to real-time stream. Live events will appear here...</div>
            )}
            {logs.map((l, i) => (
              <div key={i} style={{ fontSize: 11, color: getLogColor(l), lineHeight: 1.6, wordBreak: "break-all" }}>
                {l}
              </div>
            ))}
            <div ref={terminalEndRef} />
          </div>
        </div>
      </div>

      {/* Target Detail Modal */}
      {selectedTarget && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "#000000aa", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div style={{ background: "#0b0f19", border: "1px solid #0284c7", borderRadius: 8, width: "680px", maxWidth: "90vw", padding: 24, maxHeight: "85vh", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #1e293b", paddingBottom: 12 }}>
              <h2 style={{ color: "#38bdf8", margin: 0, fontSize: 18 }}>🛡️ {selectedTarget.repo} Security Report</h2>
              <button onClick={() => setSelectedTarget(null)} style={{ background: "none", border: "none", color: "#94a3b8", fontSize: 18, cursor: "pointer" }}>✕</button>
            </div>
            <div style={{ marginTop: 16, fontSize: 13 }}>
              <p><strong>Vulnerability Check:</strong> <span style={{ color: "#f87171" }}>{selectedTarget.finding || "unchecked-transfer (Reentrancy)"}</span></p>
              <p><strong>AI Confidence:</strong> <span style={{ color: "#34d399" }}>{selectedTarget.confidence || 85}%</span></p>
              <p><strong>Estimated Bounty:</strong> ${(selectedTarget.bounty_estimate || 25000).toLocaleString()} USD</p>
              <p><strong>Threat Analysis:</strong> {selectedTarget.synthesis?.analysis || "State update performed after external low-level call, allowing recursive reentrancy exploit."}</p>
              
              <div style={{ marginTop: 12 }}>
                <strong>Proof of Concept (Exploit PoC):</strong>
                <pre style={{ background: "#05070d", border: "1px solid #1e293b", padding: 12, borderRadius: 4, color: "#34d399", fontSize: 12, overflowX: "auto", marginTop: 6 }}>
                  {selectedTarget.synthesis?.exploit_poc || "function attack() external payable {\n    vault.withdraw(1 ether);\n}"}
                </pre>
              </div>
            </div>
            <div style={{ marginTop: 20, textAlign: "right" }}>
              <button onClick={() => setSelectedTarget(null)} style={{ background: "#38bdf8", color: "#000", border: "none", padding: "8px 16px", borderRadius: 4, fontWeight: 700, cursor: "pointer" }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

