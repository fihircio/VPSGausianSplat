using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using System;

namespace VPS.SDK
{
    public class VPSClient : MonoBehaviour
    {
        [Header("Backend Configuration")]
        [SerializeField] private string baseUrl = "";
        [SerializeField] private string apiKey = "";
        [SerializeField] private string sceneId;
        [SerializeField] private int requestTimeoutSeconds = 30;
        [SerializeField] private SpatialHintOptions hintOptions;

        public event Action<LocalizationResponse> OnLocalizationSuccess;
        public event Action<string> OnLocalizationFailed;
        public event Action<MultiFrameLocalizationResponse> OnMultiFrameLocalizationSuccess;

        public string BaseUrl { get => baseUrl; set => baseUrl = value; }
        public string ApiKey { get => apiKey; set => apiKey = value; }
        public string SceneId { get => sceneId; set => sceneId = value; }
        public int RequestTimeoutSeconds { get => requestTimeoutSeconds; set => requestTimeoutSeconds = value; }
        public SpatialHintOptions HintOptions { get => hintOptions; set => hintOptions = value; }

        private UnityWebRequest activeRequest;

        public void Localize(Texture2D texture)
        {
            byte[] jpegData = texture.EncodeToJPG(80);
            Localize(jpegData);
        }

        public void Localize(byte[] jpegData)
        {
            StartCoroutine(PostLocalizationRequest(jpegData));
        }

        public void LocalizeWithHints(Texture2D texture, SpatialHintOptions hints)
        {
            byte[] jpegData = texture.EncodeToJPG(80);
            StartCoroutine(PostLocalizationRequest(jpegData, hints));
        }

        public void LocalizeMulti(Texture2D[] textures)
        {
            if (textures == null || textures.Length == 0)
            {
                OnLocalizationFailed?.Invoke("No textures provided for multi-frame localization.");
                return;
            }
            byte[][] jpegFrames = new byte[textures.Length][];
            for (int i = 0; i < textures.Length; i++)
            {
                jpegFrames[i] = textures[i].EncodeToJPG(80);
            }
            StartCoroutine(PostMultiFrameRequest(jpegFrames));
        }

        public void LocalizeMulti(byte[][] jpegFrames)
        {
            StartCoroutine(PostMultiFrameRequest(jpegFrames));
        }

        public void CancelActiveRequest()
        {
            if (activeRequest != null && !activeRequest.isDone)
            {
                activeRequest.Abort();
                activeRequest.Dispose();
                activeRequest = null;
            }
        }

        private IEnumerator PostLocalizationRequest(byte[] jpegData, SpatialHintOptions hints = null)
        {
            if (string.IsNullOrEmpty(sceneId))
            {
                OnLocalizationFailed?.Invoke("Scene ID is not set.");
                yield break;
            }

            string normalizedBaseUrl = baseUrl?.TrimEnd('/');
            if (string.IsNullOrEmpty(normalizedBaseUrl))
            {
                OnLocalizationFailed?.Invoke("VPS API base URL is not set.");
                yield break;
            }

            string url = $"{normalizedBaseUrl}/vps/localize";

            List<IMultipartFormSection> formData = new List<IMultipartFormSection>
            {
                new MultipartFormDataSection("scene_id", sceneId),
                new MultipartFormFileSection("query_image", jpegData, "query.jpg", "image/jpeg")
            };

            SpatialHintOptions activeHints = hints ?? hintOptions;
            if (activeHints != null)
            {
                if (activeHints.hintPosition != null && activeHints.hintPosition.Length == 3)
                    formData.Add(new MultipartFormDataSection("hint_position", JsonUtility.ToJson(activeHints.hintPosition)));
                if (activeHints.hintRadius > 0)
                    formData.Add(new MultipartFormDataSection("hint_radius", activeHints.hintRadius.ToString()));
                if (activeHints.hintFloorHeight != null && activeHints.hintFloorHeight.Length == 2)
                    formData.Add(new MultipartFormDataSection("hint_floor_height", JsonUtility.ToJson(activeHints.hintFloorHeight)));
                if (!string.IsNullOrEmpty(activeHints.geoHint))
                    formData.Add(new MultipartFormDataSection("geo_hint", activeHints.geoHint));
            }

            using (UnityWebRequest www = UnityWebRequest.Post(url, formData))
            {
                activeRequest = www;
                www.timeout = Math.Max(0, requestTimeoutSeconds);
                if (!string.IsNullOrEmpty(apiKey))
                    www.SetRequestHeader("X-API-Key", apiKey);

                yield return www.SendWebRequest();

                if (www.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"VPS Localization Failed: {www.error}\n{www.downloadHandler.text}");
                    OnLocalizationFailed?.Invoke($"Localization request failed: {www.error}");
                }
                else
                {
                    try
                    {
                        var response = JsonUtility.FromJson<LocalizationResponse>(www.downloadHandler.text);
                        OnLocalizationSuccess?.Invoke(response);
                    }
                    catch (Exception ex)
                    {
                        Debug.LogError($"Failed to parse VPS response: {ex.Message}");
                        OnLocalizationFailed?.Invoke("Parse Error");
                    }
                }

                if (activeRequest == www)
                    activeRequest = null;
            }
        }

        private IEnumerator PostMultiFrameRequest(byte[][] jpegFrames)
        {
            if (string.IsNullOrEmpty(sceneId))
            {
                OnLocalizationFailed?.Invoke("Scene ID is not set.");
                yield break;
            }

            string normalizedBaseUrl = baseUrl?.TrimEnd('/');
            if (string.IsNullOrEmpty(normalizedBaseUrl))
            {
                OnLocalizationFailed?.Invoke("VPS API base URL is not set.");
                yield break;
            }

            string url = $"{normalizedBaseUrl}/vps/localize/multi";

            List<IMultipartFormSection> formData = new List<IMultipartFormSection>
            {
                new MultipartFormDataSection("scene_id", sceneId)
            };

            int frameCount = Mathf.Min(jpegFrames.Length, 6);
            for (int i = 0; i < frameCount; i++)
            {
                formData.Add(new MultipartFormFileSection($"image{i + 1}", jpegFrames[i], $"frame-{i}.jpg", "image/jpeg"));
            }

            if (hintOptions != null)
            {
                if (hintOptions.hintPosition != null && hintOptions.hintPosition.Length == 3)
                    formData.Add(new MultipartFormDataSection("hint_position", JsonUtility.ToJson(hintOptions.hintPosition)));
                if (hintOptions.hintRadius > 0)
                    formData.Add(new MultipartFormDataSection("hint_radius", hintOptions.hintRadius.ToString()));
            }

            using (UnityWebRequest www = UnityWebRequest.Post(url, formData))
            {
                activeRequest = www;
                www.timeout = Math.Max(0, requestTimeoutSeconds);
                if (!string.IsNullOrEmpty(apiKey))
                    www.SetRequestHeader("X-API-Key", apiKey);

                yield return www.SendWebRequest();

                if (www.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"VPS Multi-Frame Localization Failed: {www.error}\n{www.downloadHandler.text}");
                    OnLocalizationFailed?.Invoke($"Multi-frame localization request failed: {www.error}");
                }
                else
                {
                    try
                    {
                        var response = JsonUtility.FromJson<MultiFrameLocalizationResponse>(www.downloadHandler.text);
                        OnMultiFrameLocalizationSuccess?.Invoke(response);
                    }
                    catch (Exception ex)
                    {
                        Debug.LogError($"Failed to parse multi-frame VPS response: {ex.Message}");
                        OnLocalizationFailed?.Invoke("Parse Error");
                    }
                }

                if (activeRequest == www)
                    activeRequest = null;
            }
        }
    }
}
