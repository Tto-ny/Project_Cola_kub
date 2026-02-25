import React, { useContext } from 'react'
import MapDashboard from './components/MapDashboard'
import LoginScreen from './components/LoginScreen'
import { AuthProvider, AuthContext } from './contexts/AuthContext'
import './index.css'

const MainApp = () => {
  const { token } = useContext(AuthContext);

  if (!token) {
    return <LoginScreen />;
  }

  return (
    <div className="w-screen h-screen m-0 p-0 overflow-hidden relative">
      <MapDashboard />
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  )
}

export default App
