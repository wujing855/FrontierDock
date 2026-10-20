export function prefs(){try{return JSON.parse(localStorage.getItem('frontierdock-preferences')||'{}')}catch{return {}}}
export function savePrefs(value){try{localStorage.setItem('frontierdock-preferences',JSON.stringify({...prefs(),...value}))}catch{}}
