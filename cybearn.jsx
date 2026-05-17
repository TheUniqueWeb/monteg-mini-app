import { useState, useEffect, useRef, useCallback } from "react";

// ═══════════════════════════════════════════════════════════════
//  MOCK DATA (replace with real API calls in production)
// ═══════════════════════════════════════════════════════════════
const MOCK_USER = {
  telegram_id: 123456789,
  first_name: "Alex",
  username: "alexcyber",
  balance: 2480.5,
  total_earned: 5920.0,
  referral_code: "uid_123456789",
  photo_url: null,
};

const MOCK_TASKS = [
  { id: 1, title: "Follow on Twitter", description: "Follow @CybEarnOfficial and retweet our pinned post.", reward_amount: 150, task_type: "Social", task_url: "https://twitter.com", is_active: true },
  { id: 2, title: "Join Telegram Channel", description: "Join our main channel and stay for 24 hours.", reward_amount: 100, task_type: "Social", task_url: "https://t.me", is_active: true },
  { id: 3, title: "Watch Ad Video", description: "Watch the sponsored video until the end to earn coins.", reward_amount: 200, task_type: "Ad", task_url: null, is_active: true },
  { id: 4, title: "Leave a 5-Star Review", description: "Review our app and submit a screenshot as proof.", reward_amount: 300, task_type: "Custom", task_url: null, is_active: true },
  { id: 5, title: "Share Referral Link", description: "Share your referral link in 3 groups and submit screenshots.", reward_amount: 250, task_type: "Custom", task_url: null, is_active: true },
];

const MOCK_SUBMISSIONS = [
  { id: 1, task_id: 2, status: "Approved", task: { title: "Join Telegram Channel" }, reward_amount: 100, submitted_at: "2024-01-10" },
  { id: 2, task_id: 1, status: "Pending", task: { title: "Follow on Twitter" }, reward_amount: 150, submitted_at: "2024-01-12" },
];

const MOCK_LEADERBOARD = [
  { rank: 1, first_name: "CryptoKing", total_earned: 12400 },
  { rank: 2, first_name: "NeonHunter", total_earned: 9800 },
  { rank: 3, first_name: "Alex", total_earned: 5920 },
  { rank: 4, first_name: "ByteWizard", total_earned: 4200 },
  { rank: 5, first_name: "ShadowEarn", total_earned: 3100 },
];

// ═══════════════════════════════════════════════════════════════
//  UTILITY HOOKS & HELPERS
// ═══════════════════════════════════════════════════════════════
function useAnimatedCounter(target, duration = 1200) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let start = 0;
    const step = target / (duration / 16);
    const timer = setInterval(() => {
      start += step;
      if (start >= target) { setCount(target); clearInterval(timer); }
      else setCount(Math.floor(start));
    }, 16);
    return () => clearInterval(timer);
  }, [target, duration]);
  return count;
}

function Toast({ toasts, remove }) {
  return (
    <div style={{ position: "fixed", top: 20, right: 20, zIndex: 9999, display: "flex", flexDirection: "column", gap: 10 }}>
      {toasts.map(t => (
        <div key={t.id} onClick={() => remove(t.id)} style={{
          background: t.type === "success"
            ? "linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,255,136,0.05))"
            : "linear-gradient(135deg, rgba(255,50,50,0.15), rgba(255,50,50,0.05))",
          border: `1px solid ${t.type === "success" ? "rgba(0,255,136,0.4)" : "rgba(255,50,50,0.4)"}`,
          color: t.type === "success" ? "#00ff88" : "#ff5050",
          padding: "12px 20px", borderRadius: 12, backdropFilter: "blur(20px)",
          cursor: "pointer", fontFamily: "'Space Grotesk', sans-serif", fontSize: 13,
          boxShadow: t.type === "success"
            ? "0 0 20px rgba(0,255,136,0.2)"
            : "0 0 20px rgba(255,50,50,0.2)",
          animation: "slideIn 0.3s ease", display: "flex", alignItems: "center", gap: 8,
          maxWidth: 280,
        }}>
          <span>{t.type === "success" ? "✓" : "✗"}</span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  SKELETON LOADER
// ═══════════════════════════════════════════════════════════════
function Skeleton({ width = "100%", height = 20, radius = 8 }) {
  return (
    <div style={{
      width, height, borderRadius: radius,
      background: "linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 75%)",
      backgroundSize: "200% 100%",
      animation: "shimmer 1.5s infinite",
    }} />
  );
}

// ═══════════════════════════════════════════════════════════════
//  TASK CARD
// ═══════════════════════════════════════════════════════════════
function TaskCard({ task, completed, onSubmit }) {
  const [expanded, setExpanded] = useState(false);
  const [proof, setProof] = useState("");
  const typeColors = {
    Social: { bg: "rgba(88,166,255,0.1)", border: "rgba(88,166,255,0.3)", glow: "#58a6ff", icon: "🌐" },
    Ad: { bg: "rgba(255,200,0,0.1)", border: "rgba(255,200,0,0.3)", glow: "#ffc800", icon: "▶" },
    Custom: { bg: "rgba(188,140,255,0.1)", border: "rgba(188,140,255,0.3)", glow: "#bc8cff", icon: "✦" },
  };
  const colors = typeColors[task.task_type] || typeColors.Custom;

  return (
    <div style={{
      background: "rgba(13,17,23,0.8)",
      border: `1px solid ${completed ? "rgba(0,255,136,0.3)" : colors.border}`,
      borderRadius: 16, padding: 20, marginBottom: 14,
      backdropFilter: "blur(20px)",
      boxShadow: completed
        ? "0 0 20px rgba(0,255,136,0.08)"
        : `0 0 20px ${colors.glow}10`,
      transition: "all 0.3s ease",
      opacity: completed ? 0.7 : 1,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
            <span style={{
              background: colors.bg, border: `1px solid ${colors.border}`,
              color: colors.glow, fontSize: 10, padding: "2px 8px", borderRadius: 20,
              fontFamily: "'Space Grotesk', sans-serif", letterSpacing: 1, fontWeight: 600,
            }}>
              {colors.icon} {task.task_type.toUpperCase()}
            </span>
            {completed && (
              <span style={{ fontSize: 10, color: "#00ff88", background: "rgba(0,255,136,0.1)", padding: "2px 8px", borderRadius: 20 }}>
                ✓ SUBMITTED
              </span>
            )}
          </div>
          <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 14, color: "#e6edf3", marginBottom: 4 }}>
            {task.title}
          </div>
          <div style={{ color: "rgba(230,237,243,0.5)", fontSize: 12, lineHeight: 1.5 }}>
            {task.description}
          </div>
        </div>
        <div style={{ textAlign: "right", marginLeft: 16 }}>
          <div style={{
            fontFamily: "'Orbitron', sans-serif", fontSize: 20, fontWeight: 700,
            color: colors.glow, textShadow: `0 0 20px ${colors.glow}60`,
          }}>
            +{task.reward_amount}
          </div>
          <div style={{ fontSize: 10, color: "rgba(230,237,243,0.4)", marginTop: 2 }}>⚡ COINS</div>
        </div>
      </div>

      {!completed && (
        <div style={{ marginTop: 14 }}>
          {!expanded ? (
            <button
              onClick={() => { if (task.task_url) window.open(task.task_url); setExpanded(true); }}
              style={{
                width: "100%", padding: "10px 0", borderRadius: 10, border: "none",
                background: `linear-gradient(135deg, ${colors.glow}20, ${colors.glow}10)`,
                color: colors.glow, fontFamily: "'Space Grotesk', sans-serif",
                fontSize: 13, fontWeight: 600, cursor: "pointer",
                border: `1px solid ${colors.border}`,
                transition: "all 0.2s ease",
              }}
              onMouseEnter={e => e.target.style.boxShadow = `0 0 20px ${colors.glow}30`}
              onMouseLeave={e => e.target.style.boxShadow = "none"}
            >
              {task.task_type === "Ad" ? "▶ Watch Ad" : "→ Start Task"}
            </button>
          ) : (
            <div style={{ animation: "fadeIn 0.3s ease" }}>
              <textarea
                value={proof}
                onChange={e => setProof(e.target.value)}
                placeholder="Paste proof link, username, or describe what you did…"
                style={{
                  width: "100%", minHeight: 70, background: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10,
                  color: "#e6edf3", fontFamily: "'Space Grotesk', sans-serif",
                  fontSize: 12, padding: 12, resize: "none", outline: "none",
                  boxSizing: "border-box", marginBottom: 10,
                }}
              />
              <button
                onClick={() => { if (proof.trim()) { onSubmit(task.id, proof); setExpanded(false); setProof(""); } }}
                style={{
                  width: "100%", padding: "10px 0", borderRadius: 10, border: "none",
                  background: proof.trim()
                    ? "linear-gradient(135deg, #00ff88, #00cc6a)"
                    : "rgba(255,255,255,0.05)",
                  color: proof.trim() ? "#0d1117" : "rgba(255,255,255,0.2)",
                  fontFamily: "'Orbitron', sans-serif", fontSize: 12,
                  fontWeight: 700, cursor: proof.trim() ? "pointer" : "default",
                  transition: "all 0.3s ease",
                  boxShadow: proof.trim() ? "0 0 20px rgba(0,255,136,0.3)" : "none",
                }}
              >
                ⚡ SUBMIT PROOF
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  PAGES
// ═══════════════════════════════════════════════════════════════
function HomePage({ user, addToast }) {
  const animBalance = useAnimatedCounter(Math.floor(user.balance));
  const animEarned = useAnimatedCounter(Math.floor(user.total_earned));

  return (
    <div style={{ animation: "pageIn 0.4s ease" }}>
      {/* Profile Card */}
      <div style={{
        background: "linear-gradient(135deg, rgba(0,255,136,0.08) 0%, rgba(88,166,255,0.08) 100%)",
        border: "1px solid rgba(0,255,136,0.2)",
        borderRadius: 20, padding: 24, marginBottom: 20,
        backdropFilter: "blur(30px)",
        boxShadow: "0 0 40px rgba(0,255,136,0.05)",
        position: "relative", overflow: "hidden",
      }}>
        {/* Grid overlay */}
        <div style={{
          position: "absolute", inset: 0, opacity: 0.03,
          backgroundImage: "linear-gradient(rgba(0,255,136,1) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,136,1) 1px, transparent 1px)",
          backgroundSize: "30px 30px",
        }} />

        <div style={{ position: "relative" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 20 }}>
            <div style={{
              width: 52, height: 52, borderRadius: "50%",
              background: "linear-gradient(135deg, #00ff88, #58a6ff)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 22, fontWeight: 700, color: "#0d1117",
              boxShadow: "0 0 20px rgba(0,255,136,0.4)",
              fontFamily: "'Orbitron', sans-serif",
            }}>
              {user.first_name[0]}
            </div>
            <div>
              <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 16, color: "#e6edf3", fontWeight: 700 }}>
                {user.first_name}
              </div>
              <div style={{ fontSize: 11, color: "rgba(0,255,136,0.7)", marginTop: 2 }}>
                @{user.username} · ACTIVE EARNER
              </div>
            </div>
          </div>

          {/* Balance Display */}
          <div style={{ textAlign: "center", marginBottom: 20 }}>
            <div style={{ fontSize: 11, color: "rgba(230,237,243,0.4)", letterSpacing: 3, marginBottom: 8, fontFamily: "'Space Grotesk', sans-serif" }}>
              CURRENT BALANCE
            </div>
            <div style={{
              fontFamily: "'Orbitron', sans-serif", fontSize: 42, fontWeight: 900,
              background: "linear-gradient(135deg, #00ff88, #58a6ff)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              textShadow: "none", lineHeight: 1,
            }}>
              {animBalance.toLocaleString()}
            </div>
            <div style={{ color: "rgba(0,255,136,0.6)", fontSize: 13, marginTop: 6, fontFamily: "'Space Grotesk', sans-serif" }}>
              ⚡ COINS
            </div>
          </div>

          {/* Stats Row */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {[
              { label: "TOTAL EARNED", value: animEarned.toLocaleString(), color: "#bc8cff" },
              { label: "REFERRALS", value: "12", color: "#ffc800" },
            ].map(stat => (
              <div key={stat.label} style={{
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 12, padding: "12px 16px", textAlign: "center",
              }}>
                <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 20, fontWeight: 700, color: stat.color }}>
                  {stat.value}
                </div>
                <div style={{ fontSize: 9, color: "rgba(230,237,243,0.4)", marginTop: 4, letterSpacing: 2, fontFamily: "'Space Grotesk', sans-serif" }}>
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
        {[
          { icon: "⚡", label: "Earn Now", sub: "Complete tasks", color: "#00ff88", pulse: true },
          { icon: "👥", label: "Refer & Earn", sub: "Get commissions", color: "#58a6ff" },
          { icon: "💸", label: "Withdraw", sub: "Cash out coins", color: "#bc8cff" },
          { icon: "🏆", label: "Leaderboard", sub: "See top earners", color: "#ffc800" },
        ].map(action => (
          <div key={action.label} style={{
            background: "rgba(13,17,23,0.8)",
            border: `1px solid ${action.color}20`,
            borderRadius: 14, padding: "16px 14px", cursor: "pointer",
            backdropFilter: "blur(20px)", transition: "all 0.3s ease",
            position: "relative", overflow: "hidden",
          }}
            onMouseEnter={e => {
              e.currentTarget.style.borderColor = `${action.color}50`;
              e.currentTarget.style.boxShadow = `0 0 20px ${action.color}15`;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.borderColor = `${action.color}20`;
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            {action.pulse && (
              <div style={{
                position: "absolute", top: 8, right: 8, width: 8, height: 8,
                background: action.color, borderRadius: "50%",
                boxShadow: `0 0 8px ${action.color}`,
                animation: "pulse 2s infinite",
              }} />
            )}
            <div style={{ fontSize: 24, marginBottom: 8 }}>{action.icon}</div>
            <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 12, color: action.color, fontWeight: 700 }}>
              {action.label}
            </div>
            <div style={{ fontSize: 10, color: "rgba(230,237,243,0.4)", marginTop: 3, fontFamily: "'Space Grotesk', sans-serif" }}>
              {action.sub}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function EarnPage({ addToast }) {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [submissions, setSubmissions] = useState([]);

  useEffect(() => {
    setTimeout(() => {
      setTasks(MOCK_TASKS);
      setSubmissions(MOCK_SUBMISSIONS);
      setLoading(false);
    }, 1200);
  }, []);

  const handleSubmit = (taskId, proof) => {
    setSubmissions(prev => [...prev, { task_id: taskId, status: "Pending" }]);
    addToast("Task submitted! Awaiting admin review.", "success");
  };

  const completedTaskIds = new Set(submissions.map(s => s.task_id));

  return (
    <div style={{ animation: "pageIn 0.4s ease" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 18, color: "#e6edf3", fontWeight: 700 }}>
          Available Tasks
        </div>
        <div style={{ color: "rgba(230,237,243,0.4)", fontSize: 12, marginTop: 4, fontFamily: "'Space Grotesk', sans-serif" }}>
          Complete tasks to earn ⚡ Coins
        </div>
      </div>

      {loading ? (
        Array(3).fill(0).map((_, i) => (
          <div key={i} style={{ marginBottom: 14 }}>
            <Skeleton height={120} radius={16} />
          </div>
        ))
      ) : (
        tasks.map(task => (
          <TaskCard
            key={task.id}
            task={task}
            completed={completedTaskIds.has(task.id)}
            onSubmit={handleSubmit}
          />
        ))
      )}
    </div>
  );
}

function ReferralPage({ user, addToast }) {
  const referralLink = `https://t.me/cybearn_bot?start=${user.referral_code}`;

  const copyLink = () => {
    navigator.clipboard?.writeText(referralLink);
    addToast("Referral link copied!", "success");
  };

  return (
    <div style={{ animation: "pageIn 0.4s ease" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 18, color: "#e6edf3", fontWeight: 700 }}>
          Refer & Earn
        </div>
        <div style={{ color: "rgba(230,237,243,0.4)", fontSize: 12, marginTop: 4, fontFamily: "'Space Grotesk', sans-serif" }}>
          Earn commissions on 2 levels
        </div>
      </div>

      {/* Commission levels */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
        {[
          { level: "L1", pct: "10%", desc: "Direct referrals", color: "#00ff88" },
          { level: "L2", pct: "5%", desc: "Their referrals", color: "#58a6ff" },
        ].map(l => (
          <div key={l.level} style={{
            background: "rgba(13,17,23,0.8)", border: `1px solid ${l.color}20`,
            borderRadius: 14, padding: 16, textAlign: "center",
            backdropFilter: "blur(20px)",
          }}>
            <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 28, color: l.color, fontWeight: 900, textShadow: `0 0 20px ${l.color}60` }}>
              {l.pct}
            </div>
            <div style={{ fontSize: 11, fontWeight: 700, color: l.color, marginTop: 4, fontFamily: "'Space Grotesk', sans-serif" }}>
              {l.level} COMMISSION
            </div>
            <div style={{ fontSize: 10, color: "rgba(230,237,243,0.4)", marginTop: 3 }}>{l.desc}</div>
          </div>
        ))}
      </div>

      {/* Referral link card */}
      <div style={{
        background: "rgba(13,17,23,0.8)", border: "1px solid rgba(0,255,136,0.2)",
        borderRadius: 16, padding: 20, marginBottom: 16, backdropFilter: "blur(20px)",
      }}>
        <div style={{ fontSize: 11, color: "rgba(230,237,243,0.4)", letterSpacing: 2, marginBottom: 10, fontFamily: "'Space Grotesk', sans-serif" }}>
          YOUR REFERRAL LINK
        </div>
        <div style={{
          background: "rgba(0,255,136,0.05)", border: "1px solid rgba(0,255,136,0.15)",
          borderRadius: 10, padding: "10px 14px",
          fontFamily: "monospace", fontSize: 11, color: "#00ff88",
          wordBreak: "break-all", marginBottom: 12, lineHeight: 1.6,
        }}>
          {referralLink}
        </div>
        <button onClick={copyLink} style={{
          width: "100%", padding: "12px 0", borderRadius: 10, border: "none",
          background: "linear-gradient(135deg, #00ff88, #00cc6a)",
          color: "#0d1117", fontFamily: "'Orbitron', sans-serif",
          fontSize: 13, fontWeight: 700, cursor: "pointer",
          boxShadow: "0 0 20px rgba(0,255,136,0.3)",
        }}>
          📋 COPY REFERRAL LINK
        </button>
      </div>

      {/* Stats */}
      <div style={{
        background: "rgba(13,17,23,0.8)", border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16, padding: 20, backdropFilter: "blur(20px)",
      }}>
        <div style={{ fontSize: 11, color: "rgba(230,237,243,0.4)", letterSpacing: 2, marginBottom: 16, fontFamily: "'Space Grotesk', sans-serif" }}>
          REFERRAL STATS
        </div>
        {[
          { label: "Total Referrals", value: "12 users" },
          { label: "Commission Earned", value: "640 ⚡" },
          { label: "Pending Commission", value: "120 ⚡" },
        ].map(stat => (
          <div key={stat.label} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.05)",
          }}>
            <span style={{ color: "rgba(230,237,243,0.6)", fontSize: 13, fontFamily: "'Space Grotesk', sans-serif" }}>
              {stat.label}
            </span>
            <span style={{ color: "#e6edf3", fontFamily: "'Orbitron', sans-serif", fontSize: 13, fontWeight: 700 }}>
              {stat.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LeaderboardPage() {
  const [loading, setLoading] = useState(true);
  const [leaders, setLeaders] = useState([]);

  useEffect(() => {
    setTimeout(() => { setLeaders(MOCK_LEADERBOARD); setLoading(false); }, 800);
  }, []);

  const medals = ["🥇", "🥈", "🥉"];
  const rankColors = ["#ffc800", "#e6edf3", "#bc8cff"];

  return (
    <div style={{ animation: "pageIn 0.4s ease" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 18, color: "#e6edf3", fontWeight: 700 }}>
          Leaderboard
        </div>
        <div style={{ color: "rgba(230,237,243,0.4)", fontSize: 12, marginTop: 4, fontFamily: "'Space Grotesk', sans-serif" }}>
          Top ⚡ earners this month
        </div>
      </div>

      {loading ? (
        Array(5).fill(0).map((_, i) => <div key={i} style={{ marginBottom: 10 }}><Skeleton height={64} radius={12} /></div>)
      ) : (
        leaders.map((user, i) => (
          <div key={user.rank} style={{
            background: i < 3
              ? `linear-gradient(135deg, ${rankColors[i]}08, rgba(13,17,23,0.8))`
              : "rgba(13,17,23,0.6)",
            border: `1px solid ${i < 3 ? `${rankColors[i]}20` : "rgba(255,255,255,0.06)"}`,
            borderRadius: 12, padding: "14px 16px", marginBottom: 10,
            display: "flex", alignItems: "center", gap: 14,
            backdropFilter: "blur(20px)",
            animation: `slideUp ${0.1 + i * 0.05}s ease both`,
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: "50%",
              background: i < 3 ? `${rankColors[i]}15` : "rgba(255,255,255,0.05)",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: i < 3 ? 18 : 13,
              fontFamily: "'Orbitron', sans-serif", fontWeight: 700,
              color: i < 3 ? rankColors[i] : "rgba(230,237,243,0.4)",
            }}>
              {i < 3 ? medals[i] : `#${user.rank}`}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 14, fontWeight: 600, color: "#e6edf3" }}>
                {user.first_name}
              </div>
            </div>
            <div style={{
              fontFamily: "'Orbitron', sans-serif", fontSize: 15, fontWeight: 700,
              color: i < 3 ? rankColors[i] : "#e6edf3",
              textShadow: i < 3 ? `0 0 15px ${rankColors[i]}60` : "none",
            }}>
              {user.total_earned.toLocaleString()} ⚡
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function ProfilePage({ user, addToast }) {
  const [wallet, setWallet] = useState(user.wallet_address || "");

  return (
    <div style={{ animation: "pageIn 0.4s ease" }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 18, color: "#e6edf3", fontWeight: 700 }}>
          My Profile
        </div>
      </div>

      {/* Avatar */}
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <div style={{
          width: 80, height: 80, borderRadius: "50%", margin: "0 auto 12px",
          background: "linear-gradient(135deg, #00ff88, #58a6ff)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 32, fontWeight: 700, color: "#0d1117",
          fontFamily: "'Orbitron', sans-serif",
          boxShadow: "0 0 30px rgba(0,255,136,0.4)",
        }}>
          {user.first_name[0]}
        </div>
        <div style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 18, color: "#e6edf3" }}>
          {user.first_name}
        </div>
        <div style={{ color: "rgba(0,255,136,0.6)", fontSize: 12, marginTop: 4 }}>@{user.username}</div>
      </div>

      {/* Wallet */}
      <div style={{
        background: "rgba(13,17,23,0.8)", border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16, padding: 20, marginBottom: 16, backdropFilter: "blur(20px)",
      }}>
        <div style={{ fontSize: 11, color: "rgba(230,237,243,0.4)", letterSpacing: 2, marginBottom: 12, fontFamily: "'Space Grotesk', sans-serif" }}>
          WALLET ADDRESS
        </div>
        <input
          value={wallet}
          onChange={e => setWallet(e.target.value)}
          placeholder="Enter your TON / ETH wallet address"
          style={{
            width: "100%", background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.1)", borderRadius: 10,
            color: "#e6edf3", fontFamily: "monospace", fontSize: 12,
            padding: "12px 14px", outline: "none", boxSizing: "border-box",
            marginBottom: 12,
          }}
        />
        <button onClick={() => addToast("Wallet address saved!", "success")} style={{
          width: "100%", padding: "12px 0", borderRadius: 10, border: "none",
          background: "linear-gradient(135deg, rgba(88,166,255,0.2), rgba(88,166,255,0.1))",
          color: "#58a6ff", fontFamily: "'Orbitron', sans-serif", fontSize: 12,
          fontWeight: 700, cursor: "pointer",
          border: "1px solid rgba(88,166,255,0.3)",
        }}>
          SAVE WALLET
        </button>
      </div>

      {/* Stats */}
      <div style={{
        background: "rgba(13,17,23,0.8)", border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 16, padding: 20, backdropFilter: "blur(20px)",
      }}>
        {[
          { label: "Member Since", value: "Jan 2024" },
          { label: "Balance", value: `${user.balance.toLocaleString()} ⚡` },
          { label: "Total Earned", value: `${user.total_earned.toLocaleString()} ⚡` },
          { label: "Tasks Completed", value: "8" },
        ].map(item => (
          <div key={item.label} style={{
            display: "flex", justifyContent: "space-between", padding: "12px 0",
            borderBottom: "1px solid rgba(255,255,255,0.05)",
          }}>
            <span style={{ color: "rgba(230,237,243,0.5)", fontSize: 13, fontFamily: "'Space Grotesk', sans-serif" }}>
              {item.label}
            </span>
            <span style={{ color: "#e6edf3", fontFamily: "'Orbitron', sans-serif", fontSize: 13, fontWeight: 700 }}>
              {item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
//  MAIN APP
// ═══════════════════════════════════════════════════════════════
export default function App() {
  const [activePage, setActivePage] = useState("home");
  const [toasts, setToasts] = useState([]);
  const [user] = useState(MOCK_USER);

  const addToast = useCallback((message, type = "success") => {
    const id = Date.now();
    setToasts(p => [...p, { id, message, type }]);
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), 3500);
  }, []);

  const removeToast = useCallback((id) => setToasts(p => p.filter(t => t.id !== id)), []);

  const navItems = [
    { id: "home", icon: "⌂", label: "Home" },
    { id: "earn", icon: "⚡", label: "Earn" },
    { id: "referral", icon: "👥", label: "Refer" },
    { id: "leaderboard", icon: "🏆", label: "Board" },
    { id: "profile", icon: "◉", label: "Profile" },
  ];

  const pages = {
    home: <HomePage user={user} addToast={addToast} />,
    earn: <EarnPage addToast={addToast} />,
    referral: <ReferralPage user={user} addToast={addToast} />,
    leaderboard: <LeaderboardPage />,
    profile: <ProfilePage user={user} addToast={addToast} />,
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Space+Grotesk:wght@400;500;600;700&display=swap');
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0d1117; color: #e6edf3; overflow-x: hidden; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(0,255,136,0.2); border-radius: 4px; }
        
        @keyframes pageIn {
          from { opacity: 0; transform: translateY(16px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; box-shadow: 0 0 8px currentColor; }
          50% { opacity: 0.4; box-shadow: 0 0 4px currentColor; }
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        @keyframes scanline {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100vh); }
        }
        textarea:focus, input:focus {
          border-color: rgba(0,255,136,0.3) !important;
          box-shadow: 0 0 0 2px rgba(0,255,136,0.08) !important;
        }
      `}</style>

      {/* Scan-line ambient effect */}
      <div style={{
        position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", left: 0, right: 0, height: "30vh",
          background: "linear-gradient(transparent, rgba(0,255,136,0.015), transparent)",
          animation: "scanline 8s linear infinite",
        }} />
      </div>

      {/* Background grid */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none",
        backgroundImage: "linear-gradient(rgba(0,255,136,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,136,0.03) 1px, transparent 1px)",
        backgroundSize: "50px 50px",
      }} />

      {/* Background glow blobs */}
      <div style={{ position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none", overflow: "hidden" }}>
        <div style={{
          position: "absolute", top: -100, right: -100, width: 400, height: 400,
          background: "radial-gradient(circle, rgba(0,255,136,0.06) 0%, transparent 70%)",
          borderRadius: "50%",
        }} />
        <div style={{
          position: "absolute", bottom: 100, left: -100, width: 300, height: 300,
          background: "radial-gradient(circle, rgba(88,166,255,0.05) 0%, transparent 70%)",
          borderRadius: "50%",
        }} />
      </div>

      <Toast toasts={toasts} remove={removeToast} />

      {/* Header */}
      <div style={{
        position: "sticky", top: 0, zIndex: 100,
        background: "rgba(13,17,23,0.9)", backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(0,255,136,0.1)",
        padding: "14px 20px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 28, height: 28, background: "linear-gradient(135deg, #00ff88, #58a6ff)",
            borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, fontWeight: 900, color: "#0d1117",
          }}>⚡</div>
          <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 16, fontWeight: 900, color: "#e6edf3" }}>
            CYB<span style={{ color: "#00ff88" }}>EARN</span>
          </span>
        </div>
        <div style={{
          background: "rgba(0,255,136,0.08)", border: "1px solid rgba(0,255,136,0.2)",
          borderRadius: 20, padding: "5px 12px",
          display: "flex", alignItems: "center", gap: 6,
        }}>
          <div style={{ width: 6, height: 6, background: "#00ff88", borderRadius: "50%", animation: "pulse 2s infinite" }} />
          <span style={{ fontFamily: "'Orbitron', sans-serif", fontSize: 11, color: "#00ff88", fontWeight: 700 }}>
            {user.balance.toLocaleString()} ⚡
          </span>
        </div>
      </div>

      {/* Page content */}
      <div style={{
        position: "relative", zIndex: 1,
        padding: "20px 16px 100px",
        minHeight: "calc(100vh - 57px)",
        maxWidth: 480, margin: "0 auto",
      }}>
        {pages[activePage]}
      </div>

      {/* Bottom Navigation */}
      <div style={{
        position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 100,
        background: "rgba(13,17,23,0.95)", backdropFilter: "blur(30px)",
        borderTop: "1px solid rgba(0,255,136,0.1)",
        padding: "10px 0 max(10px, env(safe-area-inset-bottom))",
        display: "flex", justifyContent: "space-around", alignItems: "center",
      }}>
        {navItems.map(item => {
          const isActive = activePage === item.id;
          return (
            <button key={item.id} onClick={() => setActivePage(item.id)} style={{
              background: "none", border: "none", cursor: "pointer",
              display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
              padding: "6px 16px", borderRadius: 12, transition: "all 0.2s ease",
              position: "relative",
            }}>
              {isActive && (
                <div style={{
                  position: "absolute", top: -1, left: "50%", transform: "translateX(-50%)",
                  width: 24, height: 2, background: "#00ff88", borderRadius: 2,
                  boxShadow: "0 0 8px #00ff88",
                }} />
              )}
              <span style={{ fontSize: 18, opacity: isActive ? 1 : 0.4, transition: "all 0.2s" }}>
                {item.icon}
              </span>
              <span style={{
                fontSize: 9, fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600,
                letterSpacing: 0.5, color: isActive ? "#00ff88" : "rgba(230,237,243,0.4)",
                transition: "all 0.2s",
              }}>
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </>
  );
      }
