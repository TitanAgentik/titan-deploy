import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/pages/Dashboard";
import { CommandCenter } from "@/pages/CommandCenter";
import { Capital } from "@/pages/Capital";
import { Risk } from "@/pages/Risk";
import { Forge } from "@/pages/Forge";
import { OpsCenter } from "@/pages/OpsCenter";
import { Pipelines } from "@/pages/Pipelines";
import { Promotions } from "@/pages/Promotions";
import { EdgeMesh } from "@/pages/EdgeMesh";
import { Signing } from "@/pages/Signing";
import { Automations } from "@/pages/Automations";
import { GoalsLab } from "@/pages/GoalsLab";
import { Identity } from "@/pages/Identity";
import { Models } from "@/pages/Models";
import { AiLog } from "@/pages/AiLog";
import { Questions } from "@/pages/Questions";
import { SkillFactory } from "@/pages/SkillFactory";
import { AgentTeams } from "@/pages/AgentTeams";
import { AgentManager } from "@/pages/AgentManager";
import { Workspace } from "@/pages/Workspace";
import { Reports } from "@/pages/Reports";
import { Settings } from "@/pages/Settings";
import { Security } from "@/pages/Security";
import { FlashLoans } from "@/pages/FlashLoans";
import { MemecoinTrench } from "@/pages/MemecoinTrench";
import { Pnl } from "@/pages/Pnl";
import { WalletTracker } from "@/pages/WalletTracker";
import { CryptoTwitter } from "@/pages/CryptoTwitter";
import { CryptoNews } from "@/pages/CryptoNews";
import { Latency } from "@/pages/Latency";
import { QuantumInspired } from "@/pages/QuantumInspired";
import { ManualControl } from "@/pages/ManualControl";
import { DeadMansSwitch } from "@/pages/DeadMansSwitch";
import { HealthVerify } from "@/pages/HealthVerify";
import { TcaScorecard } from "@/pages/TcaScorecard";
import { PowerStatus } from "@/pages/PowerStatus";
import { DecisionLog } from "@/pages/DecisionLog";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="command" element={<CommandCenter />} />
          <Route path="manual-control" element={<ManualControl />} />
          <Route path="capital" element={<Capital />} />
          <Route path="wallets" element={<WalletTracker />} />
          <Route path="pnl" element={<Pnl />} />
          <Route path="risk" element={<Risk />} />
          <Route path="dms" element={<DeadMansSwitch />} />
          <Route path="security" element={<Security />} />
          <Route path="forge" element={<Forge />} />
          <Route path="health" element={<HealthVerify />} />
          <Route path="power" element={<PowerStatus />} />
          <Route path="ops" element={<OpsCenter />} />
          <Route path="tca" element={<TcaScorecard />} />
          <Route path="pipelines" element={<Pipelines />} />
          <Route path="promotions" element={<Promotions />} />
          <Route path="edge" element={<EdgeMesh />} />
          <Route path="latency" element={<Latency />} />
          <Route path="qi-optimizer" element={<QuantumInspired />} />
          <Route path="flash-loans" element={<FlashLoans />} />
          <Route path="memecoin" element={<MemecoinTrench />} />
          <Route path="signing" element={<Signing />} />
          <Route path="automations" element={<Automations />} />
          <Route path="crypto-twitter" element={<CryptoTwitter />} />
          <Route path="crypto-news" element={<CryptoNews />} />
          <Route path="goals" element={<GoalsLab />} />
          <Route path="identity" element={<Identity />} />
          <Route path="models" element={<Models />} />
          <Route path="ai-log" element={<AiLog />} />
          <Route path="decisions" element={<DecisionLog />} />
          <Route path="questions" element={<Questions />} />
          <Route path="skills" element={<SkillFactory />} />
          <Route path="agents" element={<AgentTeams />} />
          <Route path="agent-manager" element={<AgentManager />} />
          <Route path="workspace" element={<Workspace />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
