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
