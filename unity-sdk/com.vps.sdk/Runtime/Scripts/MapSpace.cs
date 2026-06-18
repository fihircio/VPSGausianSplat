using UnityEngine;

namespace VPS.SDK
{
    public class MapSpace : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Camera arCamera;
        [SerializeField] private VPSClient vpsClient;

        [Header("Settings")]
        [SerializeField] private bool alignOnLocalization = true;
        [Range(0, 1)]
        [SerializeField] private float alignmentSmoothing = 1.0f;

        public VPSClient Client => vpsClient;

        private void OnEnable()
        {
            if (vpsClient != null)
            {
                vpsClient.OnLocalizationSuccess += HandleLocalization;
                vpsClient.OnMultiFrameLocalizationSuccess += HandleMultiFrameLocalization;
            }
        }

        private void OnDisable()
        {
            if (vpsClient != null)
            {
                vpsClient.OnLocalizationSuccess -= HandleLocalization;
                vpsClient.OnMultiFrameLocalizationSuccess -= HandleMultiFrameLocalization;
            }
        }

        private void Start()
        {
            if (arCamera == null) arCamera = Camera.main;
            if (vpsClient == null) vpsClient = GetComponent<VPSClient>();
        }

        private void HandleLocalization(LocalizationResponse response)
        {
            if (!alignOnLocalization) return;

            Vector3 camPosInMap = response.GetUnityPosition();
            Quaternion camRotInMap = response.GetUnityRotation();

            Vector3 camPosInUnity = arCamera.transform.position;
            Quaternion camRotInUnity = arCamera.transform.rotation;

            Matrix4x4 cameraWorldMatrix = Matrix4x4.TRS(camPosInUnity, camRotInUnity, Vector3.one);
            Matrix4x4 camInMapMatrix = Matrix4x4.TRS(camPosInMap, camRotInMap, Vector3.one);

            Matrix4x4 newMapSpaceMatrix = cameraWorldMatrix * camInMapMatrix.inverse;

            Vector3 targetPosition = newMapSpaceMatrix.GetColumn(3);
            Quaternion targetRotation = Quaternion.LookRotation(
                newMapSpaceMatrix.GetColumn(2),
                newMapSpaceMatrix.GetColumn(1)
            );

            if (alignmentSmoothing >= 1.0f)
            {
                transform.position = targetPosition;
                transform.rotation = targetRotation;
            }
            else
            {
                transform.position = Vector3.Lerp(transform.position, targetPosition, alignmentSmoothing);
                transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, alignmentSmoothing);
            }

            Debug.Log($"MapSpace Aligned! Confidence: {response.confidence:P1}, Inliers: {response.inliers}");
        }

        private void HandleMultiFrameLocalization(MultiFrameLocalizationResponse response)
        {
            if (!alignOnLocalization) return;

            Vector3 camPosInMap = response.GetUnityPosition();
            Quaternion camRotInMap = response.GetUnityRotation();

            Vector3 camPosInUnity = arCamera.transform.position;
            Quaternion camRotInUnity = arCamera.transform.rotation;

            Matrix4x4 cameraWorldMatrix = Matrix4x4.TRS(camPosInUnity, camRotInUnity, Vector3.one);
            Matrix4x4 camInMapMatrix = Matrix4x4.TRS(camPosInMap, camRotInMap, Vector3.one);

            Matrix4x4 newMapSpaceMatrix = cameraWorldMatrix * camInMapMatrix.inverse;

            Vector3 targetPosition = newMapSpaceMatrix.GetColumn(3);
            Quaternion targetRotation = Quaternion.LookRotation(
                newMapSpaceMatrix.GetColumn(2),
                newMapSpaceMatrix.GetColumn(1)
            );

            if (alignmentSmoothing >= 1.0f)
            {
                transform.position = targetPosition;
                transform.rotation = targetRotation;
            }
            else
            {
                transform.position = Vector3.Lerp(transform.position, targetPosition, alignmentSmoothing);
                transform.rotation = Quaternion.Slerp(transform.rotation, targetRotation, alignmentSmoothing);
            }

            string confSummary = response.frame_confidences != null
                ? string.Join(", ", response.frame_confidences)
                : "N/A";
            Debug.Log($"MapSpace Aligned (Multi-Frame)! Frames Used: {response.frames_used}, " +
                      $"Confidence: {response.confidence:P1}, Frame Confidences: [{confSummary}]");
        }

        public void RequestLocalization(Texture2D frame = null)
        {
            if (vpsClient == null) return;

            if (frame != null)
                vpsClient.Localize(frame);
            else
                Debug.LogWarning("RequestLocalization called with null frame.");
        }

        public void RequestMultiFrameLocalization(Texture2D[] frames)
        {
            if (vpsClient == null || frames == null || frames.Length == 0)
            {
                Debug.LogWarning("RequestMultiFrameLocalization called with null or empty frames.");
                return;
            }
            vpsClient.LocalizeMulti(frames);
        }
    }
}
