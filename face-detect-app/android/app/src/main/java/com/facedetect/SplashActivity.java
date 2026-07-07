package com.facedetect;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;

/**
 * Splash screen shown while the app initializes.
 * Routes to SetupActivity on first launch, or MainActivity subsequently.
 */
public class SplashActivity extends Activity {

    private static final long SPLASH_DELAY_MS = 800;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_splash);

        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            SharedPreferences prefs = getSharedPreferences(
                    SettingsActivity.PREFS_NAME, Context.MODE_PRIVATE);
            boolean configured = prefs.getBoolean(SettingsActivity.KEY_HAS_CONFIGURED, false);

            Class<?> next = configured ? MainActivity.class : SetupActivity.class;
            Intent intent = new Intent(SplashActivity.this, next);
            startActivity(intent);
            finish();
            overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out);
        }, SPLASH_DELAY_MS);
    }
}
