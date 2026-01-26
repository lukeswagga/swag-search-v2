q'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Loader2, Plus, Edit, Trash2, X } from 'lucide-react';

const BRANDS = [
  'Rick Owens',
  'Raf Simons',
  'Comme des Garcons',
  'Yohji Yamamoto',
  'Undercover',
  'Margiela',
  'Number Nine',
  'The Soloist',
  'Visvim',
  'All Brands',
];

const MARKETS = ['Yahoo Japan', 'Mercari'];

// Currency conversion constants
const JPY_PER_USD = 147;

function usdToJpy(usd: number): number {
  return Math.round(usd * JPY_PER_USD);
}

function jpyToUsd(jpy: number): number {
  return Math.round(jpy / JPY_PER_USD);
}

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

export default function FiltersPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [filters, setFilters] = useState<Filter[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [filterToDelete, setFilterToDelete] = useState<Filter | null>(null);
  const [editingFilter, setEditingFilter] = useState<Filter | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Form state
  const [filterName, setFilterName] = useState('');
  const [selectedBrands, setSelectedBrands] = useState<string[]>([]);
  const [minPriceUsd, setMinPriceUsd] = useState(0);
  const [maxPriceUsd, setMaxPriceUsd] = useState(1000);
  const [selectedMarkets, setSelectedMarkets] = useState<string[]>([]);

  // Form errors
  const [errors, setErrors] = useState<{
    name?: string;
    brands?: string;
    markets?: string;
    price?: string;
  }>({});

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://web-production-0bd84.up.railway.app';

  // Redirect if not authenticated
  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/');
    }
  }, [status, router]);

  // Fetch filters on mount
  useEffect(() => {
    if (status === 'authenticated' && session?.user?.id) {
      fetchFilters();
    }
  }, [status, session]);

  const fetchFilters = async () => {
    if (!session?.user?.id) return;

    try {
      setLoading(true);
      const response = await fetch(
        `${apiUrl}/api/filters?discord_id=${session.user.id}`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch filters');
      }

      const data = await response.json();
      setFilters(data || []);
    } catch (error) {
      console.error('Error fetching filters:', error);
      toast.error('Failed to load filters. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const validateForm = (): boolean => {
    const newErrors: typeof errors = {};

    if (!filterName.trim()) {
      newErrors.name = 'Filter name is required';
    }

    if (selectedBrands.length === 0) {
      newErrors.brands = 'Please select at least one brand';
    }

    if (selectedMarkets.length === 0) {
      newErrors.markets = 'Please select at least one market';
    }

    const min = minPriceUsd || 0;
    const max = maxPriceUsd || 1000;

    if (min < 0) {
      newErrors.price = 'Minimum price cannot be negative';
    } else if (max < min) {
      newErrors.price = 'Maximum price must be greater than minimum price';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleBrandToggle = (brand: string) => {
    if (brand === 'All Brands') {
      setSelectedBrands(['*']);
    } else {
      setSelectedBrands((prev) => {
        const filtered = prev.filter((b) => b !== '*' && b !== brand);
        return [...filtered, brand];
      });
    }
  };

  const handleMarketToggle = (market: string) => {
    setSelectedMarkets((prev) =>
      prev.includes(market)
        ? prev.filter((m) => m !== market)
        : [...prev, market]
    );
  };

  const resetForm = () => {
    setFilterName('');
    setSelectedBrands([]);
    setMinPriceUsd(0);
    setMaxPriceUsd(1000);
    setSelectedMarkets([]);
    setErrors({});
    setEditingFilter(null);
  };

  const openCreateDialog = () => {
    resetForm();
    setIsDialogOpen(true);
  };

  const openEditDialog = (filter: Filter) => {
    setEditingFilter(filter);
    setFilterName(filter.name);
    setSelectedBrands(filter.brands);
    setMinPriceUsd(jpyToUsd(filter.price_min));
    setMaxPriceUsd(filter.price_max === 999999 ? 1000 : jpyToUsd(filter.price_max));
    setSelectedMarkets(filter.markets);
    setErrors({});
    setIsDialogOpen(true);
  };

  const handleSave = async () => {
    if (!validateForm() || !session?.user?.id) return;

    setIsSaving(true);

    try {
      const min = usdToJpy(minPriceUsd || 0);
      const max = maxPriceUsd ? usdToJpy(maxPriceUsd) : 999999;

      const brands = selectedBrands.includes('*') ? ['*'] : selectedBrands;

      const payload = {
        discord_id: session.user.id,
        name: filterName.trim(),
        brands,
        price_min: min,
        price_max: max,
        markets: selectedMarkets,
      };

      let response;
      if (editingFilter) {
        // Update existing filter
        response = await fetch(`${apiUrl}/api/filters/${editingFilter.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        // Create new filter
        response = await fetch(`${apiUrl}/api/filters`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Failed to save filter' }));
        throw new Error(error.detail || 'Failed to save filter');
      }

      toast.success(editingFilter ? 'Filter updated successfully!' : 'Filter created successfully!');
      setIsDialogOpen(false);
      resetForm();
      fetchFilters();
    } catch (error) {
      console.error('Error saving filter:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to save filter. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteClick = (filter: Filter) => {
    setFilterToDelete(filter);
    setIsDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!filterToDelete || !session?.user?.id) return;

    setIsSaving(true);

    try {
      const response = await fetch(
        `${apiUrl}/api/filters/${filterToDelete.id}?discord_id=${session.user.id}`,
        { method: 'DELETE' }
      );

      if (!response.ok) {
        throw new Error('Failed to delete filter');
      }

      toast.success('Filter deleted successfully!');
      setIsDeleteDialogOpen(false);
      setFilterToDelete(null);
      fetchFilters();
    } catch (error) {
      console.error('Error deleting filter:', error);
      toast.error('Failed to delete filter. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const formatPriceRange = (minPrice: number, maxPrice: number): string => {
    if (minPrice === 0 && maxPrice === 999999) {
      return 'All prices';
    }
    const minUsd = jpyToUsd(minPrice);
    const maxUsd = jpyToUsd(maxPrice);
    
    if (minPrice === 0) {
      return `Under $${maxUsd.toLocaleString()} (¥${maxPrice.toLocaleString()})`;
    }
    if (maxPrice === 999999) {
      return `$${minUsd.toLocaleString()}+ (¥${minPrice.toLocaleString()}+)`;
    }
    return `$${minUsd.toLocaleString()} - $${maxUsd.toLocaleString()} (¥${minPrice.toLocaleString()} - ¥${maxPrice.toLocaleString()})`;
  };

  const formatBrands = (brands: string[]): string => {
    if (brands.includes('*') || brands.length === 0) {
      return 'All brands';
    }
    if (brands.length === 1) {
      return brands[0];
    }
    if (brands.length <= 3) {
      return brands.join(', ');
    }
    return `${brands.slice(0, 2).join(', ')} +${brands.length - 2} more`;
  };

  if (status === 'loading' || loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-muted-foreground">Loading filters...</p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">My Filters</h1>
            <p className="text-muted-foreground mt-1">
              Manage your filters to receive alerts for matching listings
            </p>
          </div>
          <Button onClick={openCreateDialog} size="lg">
            <Plus className="h-4 w-4 mr-2" />
            New Filter
          </Button>
        </div>

        {/* Filters List */}
        {filters.length === 0 ? (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <p className="text-muted-foreground text-lg mb-6 text-center">
                No filters yet! Create your first one to start receiving alerts.
              </p>
              <Button onClick={openCreateDialog} size="lg">
                <Plus className="h-4 w-4 mr-2" />
                Create Filter
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {filters.map((filter) => (
              <Card key={filter.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-xl mb-2">{filter.name}</CardTitle>
                      <CardDescription className="space-y-1">
                        <div>
                          <span className="font-medium">Brands:</span>{' '}
                          {formatBrands(filter.brands)}
                        </div>
                        <div>
                          <span className="font-medium">Price:</span>{' '}
                          {formatPriceRange(filter.price_min, filter.price_max)}
                        </div>
                        <div>
                          <span className="font-medium">Markets:</span>{' '}
                          {filter.markets.join(', ')}
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <span
                            className={`inline-flex items-center gap-1 ${
                              filter.active ? 'text-green-600' : 'text-muted-foreground'
                            }`}
                          >
                            <span className="h-2 w-2 rounded-full bg-current"></span>
                            {filter.active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(filter)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDeleteClick(filter)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        )}

        {/* Create/Edit Dialog */}
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingFilter ? 'Edit Filter' : 'Create Filter'}
              </DialogTitle>
              <DialogDescription>
                {editingFilter
                  ? 'Update your filter settings below.'
                  : 'Create a new filter to receive alerts for matching listings.'}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-6 py-4">
              {/* Filter Name */}
              <div className="space-y-2">
                <Label htmlFor="name">Filter Name</Label>
                <Input
                  id="name"
                  value={filterName}
                  onChange={(e) => setFilterName(e.target.value)}
                  placeholder="e.g., Rick Owens Steals"
                />
                {errors.name && (
                  <p className="text-sm text-destructive">{errors.name}</p>
                )}
              </div>

              {/* Brands */}
              <div className="space-y-2">
                <Label>Brands (select multiple)</Label>
                <div className="grid grid-cols-2 gap-3 p-4 border rounded-md">
                  {BRANDS.map((brand) => {
                    const isChecked =
                      brand === 'All Brands'
                        ? selectedBrands.includes('*')
                        : selectedBrands.includes(brand);
                    return (
                      <div key={brand} className="flex items-center space-x-2">
                        <Checkbox
                          id={`brand-${brand}`}
                          checked={isChecked}
                          onCheckedChange={() => handleBrandToggle(brand)}
                        />
                        <Label
                          htmlFor={`brand-${brand}`}
                          className="text-sm font-normal cursor-pointer"
                        >
                          {brand}
                          {brand === 'All Brands' && ' (*)'}
                        </Label>
                      </div>
                    );
                  })}
                </div>
                {errors.brands && (
                  <p className="text-sm text-destructive">{errors.brands}</p>
                )}
              </div>

              {/* Price Range */}
              <div className="space-y-2">
                <Label>Price Range ($)</Label>
                <div className="flex items-center gap-4">
                  <div className="flex-1 space-y-2">
                    <Label htmlFor="min-price" className="text-sm text-muted-foreground">
                      Min
                    </Label>
                    <Input
                      id="min-price"
                      type="number"
                      value={minPriceUsd}
                      onChange={(e) => setMinPriceUsd(Number(e.target.value) || 0)}
                      placeholder="0"
                      min="0"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      ≈ ¥{usdToJpy(minPriceUsd).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex-1 space-y-2">
                    <Label htmlFor="max-price" className="text-sm text-muted-foreground">
                      Max
                    </Label>
                    <Input
                      id="max-price"
                      type="number"
                      value={maxPriceUsd}
                      onChange={(e) => setMaxPriceUsd(Number(e.target.value) || 0)}
                      placeholder="1000"
                      min="0"
                    />
                    <p className="text-xs text-gray-400 mt-1">
                      ≈ ¥{usdToJpy(maxPriceUsd).toLocaleString()}
                    </p>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Exchange rate: ¥147 = $1
                </p>
                {errors.price && (
                  <p className="text-sm text-destructive">{errors.price}</p>
                )}
              </div>

              {/* Markets */}
              <div className="space-y-2">
                <Label>Markets</Label>
                <div className="flex gap-4 p-4 border rounded-md">
                  {MARKETS.map((market) => (
                    <div key={market} className="flex items-center space-x-2">
                      <Checkbox
                        id={`market-${market}`}
                        checked={selectedMarkets.includes(market)}
                        onCheckedChange={() => handleMarketToggle(market)}
                      />
                      <Label
                        htmlFor={`market-${market}`}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {market}
                      </Label>
                    </div>
                  ))}
                </div>
                {errors.markets && (
                  <p className="text-sm text-destructive">{errors.markets}</p>
                )}
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setIsDialogOpen(false);
                  resetForm();
                }}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button onClick={handleSave} disabled={isSaving}>
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  'Save Filter'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete Filter</DialogTitle>
              <DialogDescription>
                Are you sure you want to delete &quot;{filterToDelete?.name}&quot;? You&apos;ll
                stop receiving alerts for it.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => {
                  setIsDeleteDialogOpen(false);
                  setFilterToDelete(null);
                }}
                disabled={isSaving}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={handleDeleteConfirm}
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete'
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}

