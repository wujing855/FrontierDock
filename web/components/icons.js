const paths={
 book:'M12 5C9 3 5 3 3 4v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-3-1-6-1-9 1Zm0 0v15',
 home:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
 journals:'M4 4h5v16H4zM11 4h4v16h-4zM17 5l3-1 4 15-4 1z',
 search:'M16 16l5 5M10 17a7 7 0 1 0 0-14 7 7 0 0 0 0 14',
 topics:'M3 4h7v6H3zM14 14h7v6h-7zM14 4h7v6h-7zM6 10v7h8',
 reading:'M5 3h14v18l-7-4-7 4z',
 data:'M4 3v18h17M8 16v-4M13 16V6M18 16V9',
 menu:'M4 6h16M4 12h16M4 18h16',
 arrow:'M5 12h14m-5-5 5 5-5 5',back:'M19 12H5m5-5-5 5 5 5',
 chevron:'m9 5 7 7-7 7',down:'m6 9 6 6 6-6',close:'m6 6 12 12M6 18 18 6',
 note:'M4 3h16v18H4zM8 8h8M8 12h8M8 16h5',
 comment:'M3 4h18v13H9l-6 4zM7 8h10M7 12h6',
 expand:'M8 3H3v5M16 3h5v5M3 16v5h5M21 16v5h-5',
 sun:'M12 3V1m0 22v-2M3 12H1m22 0h-2M5 5 3 3m18 18-2-2M5 19l-2 2M21 3l-2 2M16 12a4 4 0 1 0-8 0 4 4 0 0 0 8 0',
 check:'m5 12 4 4L19 6',info:'M12 11v6m0-10v.1M21 12a9 9 0 1 0-18 0 9 9 0 0 0 18 0',
 external:'M14 3h7v7m0-7L10 14M10 3H3v18h18v-7',file:'M5 2h9l5 5v15H5zM14 2v6h5M8 12h8M8 16h8',
 filter:'M3 5h18M6 12h12M9 19h6'
};
export function icon(name,size=18){return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]||paths.book}"/></svg>`}
