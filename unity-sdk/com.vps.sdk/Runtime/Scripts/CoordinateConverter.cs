using UnityEngine;

namespace VPS.SDK
{
    public static class CoordinateConverter
    {
        /// <summary>
        /// Converts a position from OpenCV/COLMAP Right-Handed (Y-Down, Z-Forward) 
        /// to Unity Left-Handed (Y-Up, Z-Forward).
        /// </summary>
        public static Vector3 CVToUnityPosition(Vector3 cvPos)
        {
            return new Vector3(cvPos.x, -cvPos.y, cvPos.z);
        }

        /// <summary>
        /// Converts a quaternion from OpenCV/COLMAP Right-Handed (Y-Down, Z-Forward) 
        /// to Unity Left-Handed (Y-Up, Z-Forward).
        /// Expected Input: [x, y, z, w] in Right-Handed space.
        /// </summary>
        public static Quaternion CVToUnityRotation(Quaternion cvRot)
        {
            // Negate Y and W to flip from RH Y-Down to LH Y-Up
            return new Quaternion(cvRot.x, -cvRot.y, cvRot.z, -cvRot.w);
        }

        /// <summary>
        /// Helper to convert float arrays from API to Unity types.
        /// </summary>
        public static Vector3 ArrayToVector3(float[] arr)
        {
            if (arr == null || arr.Length < 3) return Vector3.zero;
            return new Vector3(arr[0], arr[1], arr[2]);
        }

        /// <summary>
        /// Helper to convert float arrays from API to Unity types.
        /// Expected [x, y, z, w]
        /// </summary>
        public static Quaternion ArrayToQuaternion(float[] arr)
        {
            if (arr == null || arr.Length < 4) return Quaternion.identity;
            return new Quaternion(arr[0], arr[1], arr[2], arr[3]);
        }
    }
}
