// LP ExpertFinish palette — swatch hexes are VISUALIZATION APPROXIMATIONS
// for the 3D flat repaint and color chips, not paint-matched values.
// Color NAMES come from the backend (/lp-package/colors) — source of truth.
export const LP_COLOR_HEX = {
  "Sand Dunes": "#C9B99A",
  "Snowscape White": "#EDEAE2",
  "Desert Stone": "#AFA28B",
  "Quarry Gray": "#8E8E8B",
  "Prairie Clay": "#A97D62",
  "Garden Sage": "#8A9384",
  "Harvest Honey": "#C9A46B",
  "Terra Brown": "#6B5748",
  "Timberland Suede": "#8B7355",
  "Tundra Gray": "#B4B6B3",
  "Cavern Steel": "#5F6B72",
  "Summit Blue": "#46617A",
  "Rapids Blue": "#7B95A3",
  "Midnight Shadow": "#3E4247",
  "Abyss Black": "#23262A",
  "Redwood Red": "#7C3A2D",
  "Bonsai Black": "#2E2A26",
  "Weathered Walnut": "#6E5B4A",
  "Aged Amber": "#9A6E42",
  "Saffron Cedar": "#B0703C",
  "Smoky Slate": "#6E6E68",
  "Washed White": "#E5DFD2",
  "Primed (paint any color)": "#DDD8CE",
};

export const lpHex = (name) => LP_COLOR_HEX[name] || null;

export const LP_GROUP_LABELS = {
  siding: "Siding",
  soffit_fascia: "Soffit & Fascia",
  opening_trim: "Opening Trim",
  osc: "Outside Corners",
  isc: "Inside Corners",
};
