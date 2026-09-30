//! Fast deterministic hashing for engine-internal scratch maps and sets.
//!
//! Rule checks build many small coordinate sets while candidates are generated; the
//! default SipHash (designed against untrusted keys) dominated that time. Keys here are
//! engine-owned coordinates and small integers, so HashDoS resistance is not needed.
//! Public state types keep `std` defaults; only internal working collections use this.
use std::hash::{BuildHasherDefault, Hasher};

/// The FxHash mix used by rustc.
#[derive(Debug, Default, Clone, Copy)]
pub struct FxHasher(u64);

const SEED: u64 = 0x51_7c_c1_b7_27_22_0a_95;

impl FxHasher {
    #[inline]
    fn mix(&mut self, word: u64) {
        self.0 = (self.0.rotate_left(5) ^ word).wrapping_mul(SEED);
    }
}

impl Hasher for FxHasher {
    #[inline]
    fn finish(&self) -> u64 {
        self.0
    }
    #[inline]
    fn write(&mut self, bytes: &[u8]) {
        let mut chunks = bytes.chunks_exact(8);
        for chunk in &mut chunks {
            let mut word = [0u8; 8];
            word.copy_from_slice(chunk);
            self.mix(u64::from_le_bytes(word));
        }
        for &byte in chunks.remainder() {
            self.mix(u64::from(byte));
        }
    }
    #[inline]
    fn write_u8(&mut self, value: u8) {
        self.mix(u64::from(value));
    }
    #[inline]
    fn write_u16(&mut self, value: u16) {
        self.mix(u64::from(value));
    }
    #[inline]
    fn write_u32(&mut self, value: u32) {
        self.mix(u64::from(value));
    }
    #[inline]
    fn write_u64(&mut self, value: u64) {
        self.mix(value);
    }
    #[inline]
    fn write_usize(&mut self, value: usize) {
        self.mix(value as u64);
    }
    #[inline]
    fn write_i32(&mut self, value: i32) {
        self.mix(u64::from(value as u32));
    }
}

pub type FxBuildHasher = BuildHasherDefault<FxHasher>;
pub type FastMap<K, V> = std::collections::HashMap<K, V, FxBuildHasher>;
pub type FastSet<K> = std::collections::HashSet<K, FxBuildHasher>;
