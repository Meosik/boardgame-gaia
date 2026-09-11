use sha2::{Digest, Sha256};
use std::{
    env, fs,
    path::{Path, PathBuf},
};

fn collect(path: &Path, files: &mut Vec<PathBuf>) -> std::io::Result<()> {
    if path.is_dir() {
        println!("cargo:rerun-if-changed={}", path.display());
        for entry in fs::read_dir(path)? {
            collect(&entry?.path(), files)?;
        }
    } else {
        files.push(path.to_owned());
    }
    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let crate_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR")?);
    let root = crate_dir.parent().ok_or("missing project root")?;
    let mut files = Vec::new();
    for name in [
        "gaia-engine/src",
        "gaia-engine/data",
        "gaia-engine/Cargo.toml",
        "gaia-rl/src",
        "gaia-rl/build.rs",
        "gaia-rl/Cargo.toml",
        "gaia-rl/Cargo.lock",
        "rust-toolchain.toml",
    ] {
        let path = root.join(name);
        if path.exists() {
            collect(&path, &mut files)?;
        }
    }
    files.sort();
    let mut combined = Sha256::new();
    let mut manifest = String::new();
    for path in files {
        println!("cargo:rerun-if-changed={}", path.display());
        let relative = path
            .strip_prefix(root)?
            .to_str()
            .ok_or("non-UTF8 source path")?;
        let digest = format!("{:x}", Sha256::digest(fs::read(&path)?));
        let line = format!("{digest}  {relative}\n");
        combined.update(line.as_bytes());
        manifest.push_str(&line);
    }
    println!(
        "cargo:rustc-env=GAIA_ENGINE_BUILD_ID={:x}",
        combined.finalize()
    );
    fs::write(
        PathBuf::from(env::var("OUT_DIR")?).join("source-manifest.txt"),
        manifest,
    )?;
    Ok(())
}
