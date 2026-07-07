package com.facedetect;

import android.content.Context;
import android.widget.Toast;
import android.util.Log;

public class JsBridge {
    private Context context;

    public JsBridge(Context context) {
        this.context = context;
    }

    @android.webkit.JavascriptInterface
    public void showToast(String message) {
        Toast.makeText(context, message, Toast.LENGTH_SHORT).show();
    }

    @android.webkit.JavascriptInterface
    public String getServerUrl() {
        // Returns the configured server URL to JavaScript
        return "http://10.0.2.2:8000";
    }

    @android.webkit.JavascriptInterface
    public void log(String message) {
        Log.d("FaceDetectJS", message);
    }
}
