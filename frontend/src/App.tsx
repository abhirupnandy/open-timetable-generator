import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ErrorBox, Loading } from "./components/States";
import { AuthProvider, isStaffRole, useSession } from "./lib/auth";
import { Constraints } from "./pages/Constraints";
import { Generate } from "./pages/Generate";
import { ImportData } from "./pages/ImportData";
import { Login } from "./pages/Login";
import { Overview } from "./pages/Overview";
import { ResourcePage } from "./pages/ResourcePage";
import { Runs } from "./pages/Runs";
import { Timetable } from "./pages/Timetable";
import { Users } from "./pages/Users";

export function App() {
  const session = useSession();

  if (session.error) {
    return (
      <div className="login-page">
        <ErrorBox error={session.error} />
      </div>
    );
  }
  if (session.data === undefined) {
    return (
      <div className="login-page">
        <Loading />
      </div>
    );
  }
  if (session.data === null) return <Login />;

  const user = session.data;
  const staff = isStaffRole(user.role);

  return (
    <AuthProvider user={user}>
      <Routes>
        <Route element={<Layout />}>
          {staff ? (
            <>
              <Route index element={<Overview />} />
              <Route path="import" element={<ImportData />} />
              <Route path="generate" element={<Generate />} />
              <Route path="runs" element={<Runs />} />
              <Route path="runs/:runId" element={<Runs />} />
              <Route path="timetable" element={<Timetable />} />
              <Route path="constraints" element={<Constraints />} />
              <Route path="data/:resource" element={<ResourcePage />} />
              {user.role === "ADMIN" && <Route path="users" element={<Users />} />}
              <Route path="*" element={<Navigate to="/" replace />} />
            </>
          ) : (
            <>
              <Route path="timetable" element={<Timetable />} />
              <Route path="*" element={<Navigate to="/timetable" replace />} />
            </>
          )}
        </Route>
      </Routes>
    </AuthProvider>
  );
}
