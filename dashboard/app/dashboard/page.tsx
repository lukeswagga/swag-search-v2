import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { authOptions } from "../api/auth/[...nextauth]/route";

interface Filter {
  id: number;
  user_id: string;
  name: string;
  brands: string[];
  price_min: number;
  price_max: number;
  markets: string[];
  active: boolean;
}

async function getFilters(discordId: string): Promise<Filter[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://web-production-0bd84.up.railway.app";
  
  try {
    const response = await fetch(
      `${apiUrl}/api/filters?discord_id=${discordId}`,
      {
        cache: "no-store", // Always fetch fresh data
      }
    );

    if (!response.ok) {
      console.error(`Failed to fetch filters: ${response.status} ${response.statusText}`);
      return [];
    }

    const filters = await response.json();
    return filters || [];
  } catch (error) {
    console.error("Error fetching filters:", error);
    return [];
  }
}

function formatPriceRange(minPrice: number, maxPrice: number): string {
  if (minPrice === 0 && maxPrice === 999999) {
    return "All prices";
  }
  if (minPrice === 0) {
    return `Under ¥${maxPrice.toLocaleString()}`;
  }
  if (maxPrice === 999999) {
    return `¥${minPrice.toLocaleString()}+`;
  }
  return `¥${minPrice.toLocaleString()} - ¥${maxPrice.toLocaleString()}`;
}

function formatBrands(brands: string[]): string {
  if (brands.includes("*") || brands.length === 0) {
    return "Any brand";
  }
  if (brands.length === 1) {
    return brands[0];
  }
  if (brands.length <= 3) {
    return brands.join(", ");
  }
  return `${brands.slice(0, 2).join(", ")} +${brands.length - 2} more`;
}

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  
  if (!session?.user) {
    redirect("/");
  }

  const discordId = session.user.id;
  const username = session.user.name || "User";
  const filters = await getFilters(discordId);
  const activeFilters = filters.filter((f) => f.active);
  const activeFilterCount = activeFilters.length;

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Welcome back, {username}
          </h1>
          <p className="text-gray-400">
            Manage your filters and view your alerts
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Active Filters Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="text-4xl font-bold mb-2">{activeFilterCount}</div>
            <div className="text-gray-400">Active Filters</div>
          </div>

          {/* Alerts Today Card */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
            <div className="text-4xl font-bold mb-2">0</div>
            <div className="text-gray-400">Alerts Today</div>
          </div>
        </div>

        {/* Filters Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-semibold">Your Active Filters</h2>
          </div>

          {activeFilters.length === 0 ? (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-12 text-center">
              <p className="text-gray-400 text-lg mb-6">
                No filters yet! Create your first one to start receiving alerts.
              </p>
              <Link
                href="/filters"
                className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-8 rounded-lg text-lg transition-colors"
              >
                Create Your First Filter
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {activeFilters.slice(0, 5).map((filter) => (
                <div
                  key={filter.id}
                  className="bg-gray-800 border border-gray-700 rounded-lg p-4 hover:border-gray-600 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg mb-2">{filter.name}</h3>
                      <div className="text-sm text-gray-400 space-y-1">
                        <div>
                          <span className="text-gray-500">Brands:</span>{" "}
                          <span className="text-gray-300">{formatBrands(filter.brands)}</span>
                        </div>
                        <div>
                          <span className="text-gray-500">Price:</span>{" "}
                          <span className="text-gray-300">
                            {formatPriceRange(filter.price_min, filter.price_max)}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500">Markets:</span>{" "}
                          <span className="text-gray-300">
                            {filter.markets.join(", ")}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {activeFilters.length > 5 && (
                <div className="text-center text-gray-400 text-sm pt-2">
                  +{activeFilters.length - 5} more filter{activeFilters.length - 5 !== 1 ? "s" : ""}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-4">
          <Link
            href="/filters"
            className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
          >
            + Create Filter
          </Link>
          <Link
            href="/feed"
            className="bg-gray-700 hover:bg-gray-600 text-white font-bold py-3 px-6 rounded-lg transition-colors"
          >
            View Feed
          </Link>
        </div>
      </div>
    </div>
  );
}

