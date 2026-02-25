export type NbmsNavItem = {
  route: string;
  label: string;
  icon: string;
  public?: boolean;
  capability?: string;
  badge?: string;
};

export type NbmsNavGroup = {
  label: string;
  items: NbmsNavItem[];
};

export type NbmsPinnedView = {
  id: string;
  name: string;
  namespace: 'indicators' | 'registries' | 'downloads';
  route: string;
  queryParams: Record<string, string>;
};
