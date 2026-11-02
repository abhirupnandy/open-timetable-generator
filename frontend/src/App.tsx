import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { Constraints } from "./pages/Constraints";
import { Generate } from "./pages/Generate";
import { Overview } from "./pages/Overview";
import { ResourcePage } from "./pages/ResourcePage";
import { Timetable } from "./pages/Timetable";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="generate" element={<Generate />} />
        <Route path="timetable" element={<Timetable />} />
        <Route path="constraints" element={<Constraints />} />
        <Route path="data/:resource" element={<ResourcePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
