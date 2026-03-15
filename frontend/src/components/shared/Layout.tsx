import {
  Link,
  useLocation,
  // useNavigate
} from "react-router-dom";
// import { useAuth } from "../../context/AuthContext";

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  // const navigate = useNavigate();
  // const { isAuthenticated, logout } = useAuth();

  // function handleLogout() {
  //   logout();
  //   navigate("/login", { replace: true });
  // }

  const navItems = [{ path: "/admin", label: "Admin Dashboard" }];

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link to="/" className="text-xl font-bold text-gray-900">
                Apex Recovery
              </Link>
            </div>
            <div className="ml-10 flex space-x-4 items-center">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    location.pathname === item.path
                      ? "bg-gray-900 text-white"
                      : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
            </div>
            {/* {isAuthenticated && (
              <div className="flex items-center">
                <button
                  onClick={handleLogout}
                  className="px-3 py-2 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900 transition-colors"
                >
                  Sign out
                </button>
              </div>
            )} */}
          </div>
        </div>
      </nav>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
