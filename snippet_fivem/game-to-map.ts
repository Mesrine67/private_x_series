/**
 * Game coordinate to Map coordinate converter
 * Uses polynomial band-based regression (from ox_lib / coffeelot's approach)
 * This is the server-side (TypeScript) implementation for the API.
 */

export const MAP_CONFIG = {
  center_x: 117.3,
  center_y: 172.8,
  scale_x: 0.02072,
  scale_y: 0.0205,
  minZoom: 1,
  maxZoom: 5,
  defaultZoom: 3,
  // Ocean color matching the GTA V map tiles
  backgroundColor: "#0fa8d2",
} as const

export type MapStyle = "satellite" | "atlas" | "grid" | "tilted"

export const MAP_STYLES: Record<
  MapStyle,
  { url: string; maxZoom: number; label: string; icon: string }
> = {
  satellite: {
    url: "https://raw.githubusercontent.com/kibradev/interactive-map/main/mapStyles/styleSatelite/{z}/{x}/{y}.jpg",
    maxZoom: 8,
    label: "Satellite",
    icon: "satellite",
  },
  atlas: {
    url: "https://raw.githubusercontent.com/kibradev/interactive-map/main/mapStyles/styleAtlas/{z}/{x}/{y}.jpg",
    maxZoom: 5,
    label: "Atlas",
    icon: "map",
  },
  grid: {
    url: "https://raw.githubusercontent.com/kibradev/interactive-map/main/mapStyles/styleGrid/{z}/{x}/{y}.png",
    maxZoom: 5,
    label: "Grid",
    icon: "grid",
  },
}

const transforms = {
  band1: {
    longitude: { a: -3.03663255576895e-9, b: 0.0200175350440883, c: -97.211789757094 },
    latitude: { a: 6.23122700084464e-14, b: 4.20129073856139e-10, c: 2.33168021020044e-6, d: 0.0240131069198339, e: 14.1346597090657 },
  },
  band2: {
    longitude: { a: 2.04927570146569e-8, b: 0.0199382651698616, c: -97.2328189248356 },
    latitude: { a: -5.48114969721267e-14, b: -1.7644651413213e-10, c: -6.69398961485353e-7, d: 0.019446455419011, e: 11.948776738614 },
  },
  band3: {
    longitude: { a: 1.14491978248603e-8, b: 0.0199665146367798, c: -97.2865999889282 },
    latitude: { a: -7.50970630543969e-15, b: 2.42587620752238e-10, c: -3.39800162545523e-6, d: 0.02514652658967, e: 7.49474095495398 },
  },
  band4: {
    longitude: { a: -4.51344244634536e-8, b: 0.0200135106227036, c: -97.1355799536373 },
    latitude: { a: -2.33545837309061e-14, b: 6.7194107532233e-10, c: -7.73181068541832e-6, d: 0.0443322941450463, e: -23.9182574396233 },
  },
}

/**
 * Convert GTA V game coordinates (x, y) to map coordinates (longitude, latitude)
 * Uses band-based polynomial regression for accuracy across the full map.
 */
export function gameToMap(x: number, y: number): { lng: number; lat: number } {
  let t: (typeof transforms)["band1"]

  if (y < -1000) {
    t = transforms.band1
  } else if (y < 2000) {
    t = transforms.band2
  } else if (y < 5000) {
    t = transforms.band3
  } else {
    t = transforms.band4
  }

  const lng = t.longitude.a * x ** 2 + t.longitude.b * x + t.longitude.c
  const lat =
    t.latitude.a * y ** 4 +
    t.latitude.b * y ** 3 +
    t.latitude.c * y ** 2 +
    t.latitude.d * y +
    t.latitude.e

  return { lng, lat }
}
