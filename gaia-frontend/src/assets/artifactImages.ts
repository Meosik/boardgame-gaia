import artifact01 from './artifacts/normalized/artifact_01.webp';
import artifact02 from './artifacts/normalized/artifact_02.webp';
import artifact03 from './artifacts/normalized/artifact_03.webp';
import artifact04 from './artifacts/normalized/artifact_04.webp';
import artifact05 from './artifacts/normalized/artifact_05.webp';
import artifact06 from './artifacts/normalized/artifact_06.webp';
import artifact07 from './artifacts/normalized/artifact_07.webp';
import artifact08 from './artifacts/normalized/artifact_08.webp';
import artifact09 from './artifacts/normalized/artifact_09.webp';
import artifact10 from './artifacts/normalized/artifact_10.webp';
import artifact11 from './artifacts/normalized/artifact_11.webp';
import artifact12 from './artifacts/normalized/artifact_12.webp';
import artifact13 from './artifacts/normalized/artifact_13.webp';

const byId: Record<number, string> = {
  1: artifact01,
  2: artifact02,
  3: artifact03,
  4: artifact04,
  5: artifact05,
  6: artifact06,
  7: artifact07,
  8: artifact08,
  9: artifact09,
  10: artifact10,
  11: artifact11,
  12: artifact12,
  13: artifact13,
};

export function artifactImageSrc(artifactId: number): string | undefined {
  return byId[artifactId];
}
