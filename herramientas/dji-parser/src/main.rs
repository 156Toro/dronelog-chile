//! dji-parser: lee un FlightRecord de DJI Fly y escribe en stdout un JSON con
//! la versión, los detalles del vuelo y los frames descifrados.
//!
//! Uso: dji-parser <archivo.txt> [--keychains <keychains.json>]
//! La App Key de DJI Open API se lee de la variable de entorno DJI_API_KEY.
//! Códigos de salida: 0 = ok, 2 = archivo no es un registro DJI, 3 = no se pudo descifrar.
use dji_log_parser::DJILog;
use serde_json::json;
use std::{env, fs, process};

fn salir(codigo: i32, mensaje: &str) -> ! {
    eprintln!("{}", mensaje);
    process::exit(codigo)
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        salir(1, "uso: dji-parser <archivo.txt> [--keychains <archivo.json>]");
    }
    let bytes = fs::read(&args[1]).unwrap_or_else(|e| salir(1, &format!("no se pudo leer el archivo: {e}")));
    let parser = DJILog::from_bytes(bytes).unwrap_or_else(|e| salir(2, &format!("no es un registro de vuelo DJI válido: {e}")));

    let keychains = if parser.version < 13 {
        None
    } else if let Some(pos) = args.iter().position(|a| a == "--keychains") {
        let ruta = args.get(pos + 1).unwrap_or_else(|| salir(1, "falta la ruta de --keychains"));
        let texto = fs::read_to_string(ruta).unwrap_or_else(|e| salir(1, &format!("no se pudo leer keychains: {e}")));
        Some(serde_json::from_str(&texto).unwrap_or_else(|e| salir(1, &format!("keychains inválidos: {e}"))))
    } else {
        let clave = env::var("DJI_API_KEY").unwrap_or_else(|_| salir(3, "falta la variable DJI_API_KEY"));
        Some(parser.fetch_keychains(&clave).unwrap_or_else(|e| salir(3, &format!("DJI rechazó la solicitud de claves: {e}"))))
    };

    let frames = parser.frames(keychains).unwrap_or_else(|e| salir(3, &format!("no se pudo descifrar el registro: {e}")));
    let salida = json!({ "version": parser.version, "details": parser.details, "frames": frames });
    println!("{}", salida);
}
