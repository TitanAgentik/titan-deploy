import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/pages/Dashboard";
import { CommandCenter } from "@/pages/CommandCenter";
import { Forge } from "@/pages/Forge";
import { OpsCenter } from "@/pages/OpsCenter";
import { Automations } from "@/pages/Automations";
import { GoalsLab } from "@/pages/GoalsLab";
import { Identity } from "@/pages/Identity";
import { AiLog } from "@/pages/AiLog";
import { Questions } from "@/pages/Questions";
import { SkillFactory } from "@/pages/SkillFactory";
import { AgentTeams } from "@/pages/AgentTeams";
import { Workspace } from "@/pages/Workspace";
import { Reports } from "@/pages/Reports";
import { Settings } from "@/pages/Settings";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="command" element={<CommandCenter />} />
          <Route path="forge" element={<Forge />} />
          <Route path="ops" element={<OpsCenter />} />
          <Route path="automations" element={<Automations />} />
          <Route path="goals" element={<GoalsLab />} />
          <Route path="identity" element={<Identity />} />
          <Route path="ai-log" element={<AiLog />} />
          <Route path="questions" element={<Questions />} />
          <Route path="skills" element={<SkillFactory />} />
          <Route path="agents" element={<AgentTeams />} />
          <Route path="workspace" element={<Workspace />} />
          <Route path="reports" element={<Reports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
