package com.facedetect;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;

import androidx.appcompat.app.AppCompatActivity;

/**
 * Settings screen for configuring the backend server URL.
 */
public class SettingsActivity extends AppCompatActivity {

    private EditText serverUrlInput;
    static final String PREFS_NAME = "FaceDetectPrefs";
    static final String KEY_SERVER_URL = "server_url";
    static final String KEY_HAS_CONFIGURED = "has_configured";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_settings);

        serverUrlInput = findViewById(R.id.server_url_input);

        // Load saved server URL
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String savedUrl = prefs.getString(KEY_SERVER_URL, getString(R.string.server_url));
        serverUrlInput.setText(savedUrl);

        Button saveBtn = findViewById(R.id.save_btn);
        saveBtn.setOnClickListener(v -> {
            String url = serverUrlInput.getText().toString().trim();
            if (!url.isEmpty()) {
                // Ensure URL ends properly
                if (!url.endsWith("/")) {
                    url += "/";
                }
                SharedPreferences.Editor editor = prefs.edit();
                editor.putString(KEY_SERVER_URL, url);
                editor.putBoolean(KEY_HAS_CONFIGURED, true);
                editor.apply();
            }
            finish();
        });

        Button cancelBtn = findViewById(R.id.cancel_btn);
        cancelBtn.setOnClickListener(v -> finish());
    }

    public static String getServerUrl(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getString(KEY_SERVER_URL, context.getString(R.string.server_url));
    }
}
