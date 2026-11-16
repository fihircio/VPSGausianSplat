# Supported Map Upload Sources

This page describes the inputs accepted by `POST /scene/upload` in the current backend. An accepted upload is only the start of map processing; it is not a guarantee that reconstruction or localization will succeed.

## Accepted capture inputs

| Input | Extensions | Processing path |
| --- | --- | --- |
| Video capture | `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm` | Extract frames, run COLMAP structure-from-motion, generate a point-cloud/splat output, and build the VPS feature index. |
| Still image | `.jpg`, `.jpeg`, `.png`, `.bmp` | Copy the image as one frame, then run the same reconstruction and indexing stages. A still image may not contain enough multi-view information to produce a usable map. |

The default maximum upload size is **500 MB per file** (`MAX_UPLOAD_SIZE_MB` / `max_upload_size_mb`); a deployment can configure another limit. Requests above the configured limit return HTTP `413`. Unsupported extensions and explicit image/video MIME-type mismatches return HTTP `415`. Generic MIME types such as `application/octet-stream` are accepted based on the filename extension. The server does not inspect/decode the entire file during upload, so a corrupt or mislabeled file can still be accepted and then fail during processing; check the scene status and error message after processing.

## Not accepted as map uploads

The current endpoint does not ingest Gaussian `.ply` files, COLMAP models, E57, OBJ/GLB meshes, LAS/LAZ point clouds, Matterport exports, or 360-camera source video. A PLY produced by the reconstruction pipeline is an **output artifact**, not an alternate upload source. A standalone PLY does not provide the captured image frames and camera poses needed to build this project's VPS feature index. Supporting PLY as a viewer-only import would be a separate workflow and must not be presented as a localized/ready map.

Google 3D synthetic AOIs are also separate from customer `Scene` uploads. Their manifests, permission records, and evaluation artifacts live under `backend/storage/google3d/`; they are not processed by `POST /scene/upload`.

## Readiness and failure handling

An upload creates a scene in `UPLOADED` state. Processing runs frame extraction, COLMAP reconstruction, splat/point-cloud export, and VPS feature indexing. Only a scene that completes those stages reaches `READY`; processing failures are reported in the scene's `error_message` and set its status to `FAILED`. A successful HTTP upload response does not prove the file is decodable or that the footage contains enough movement, overlap, texture, or parallax for reconstruction.

For capture guidance and the API example, see [Quickstart](quickstart.md) and [Capture Protocol](capture_protocol.md).
