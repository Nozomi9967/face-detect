package com.facedetect;

import android.Manifest;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.zxing.ResultPoint;
import com.journeyapps.barcodescanner.BarcodeCallback;
import com.journeyapps.barcodescanner.BarcodeResult;
import com.journeyapps.barcodescanner.BarcodeView;

/**
 * Settings screen for configuring the backend server URL.
 * Supports manual input and QR code scanning.
 */
public class SettingsActivity extends AppCompatActivity {

    private EditText serverUrlInput;
    static final String PREFS_NAME = "FaceDetectPrefs";
    static final String KEY_SERVER_URL = "server_url";
    static final String KEY_HAS_CONFIGURED = "has_configured";
    private static final int CAMERA_REQUEST_CODE = 2001;

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

        findViewById(R.id.back_btn).setOnClickListener(v -> finish());

        View scanBtn = findViewById(R.id.scan_qr_btn);
        scanBtn.setOnClickListener(v -> startQRScan());
    }

    // ── QR 扫码 ────────────────────────────────────────────

    private void startQRScan() {
        if (!hasCameraPermission()) {
            requestCameraPermission();
            return;
        }
        launchScanner();
    }

    private boolean hasCameraPermission() {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED;
    }

    private void requestCameraPermission() {
        ActivityCompat.requestPermissions(this,
                new String[]{Manifest.permission.CAMERA}, CAMERA_REQUEST_CODE);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode,
                                           @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == CAMERA_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                launchScanner();
            } else {
                if (ActivityCompat.shouldShowRequestPermissionRationale(this,
                        Manifest.permission.CAMERA)) {
                    Toast.makeText(this, "需要相机权限才能扫码", Toast.LENGTH_SHORT).show();
                } else {
                    showPermissionDeniedDialog();
                }
            }
        }
    }

    private void showPermissionDeniedDialog() {
        new AlertDialog.Builder(this)
                .setTitle("需要相机权限")
                .setMessage("请在系统设置中允许 FaceDetect 使用相机，然后重试。")
                .setPositiveButton("去设置", (d, w) -> {
                    Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                    intent.setData(Uri.fromParts("package", getPackageName(), null));
                    startActivity(intent);
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void launchScanner() {
        try {
            BarcodeView barcodeView = new BarcodeView(this);

            FrameLayout container = new FrameLayout(this);
            container.addView(barcodeView,
                    new FrameLayout.LayoutParams(
                            FrameLayout.LayoutParams.MATCH_PARENT,
                            FrameLayout.LayoutParams.MATCH_PARENT));

            AlertDialog dialog = new AlertDialog.Builder(this)
                    .setTitle("扫描二维码")
                    .setMessage("将摄像头对准服务器页面的二维码")
                    .setCancelable(true)
                    .create();
            dialog.setView(container);

            barcodeView.decodeContinuous(new BarcodeCallback() {
                @Override
                public void barcodeResult(BarcodeResult result) {
                    if (result.getText() != null && !result.getText().isEmpty()) {
                        barcodeView.pause();
                        dialog.dismiss();
                        String scanned = result.getText().trim();
                        runOnUiThread(() -> handleScannedUrl(scanned));
                    }
                }

                @Override
                public void possibleResultPoints(
                        java.util.List<ResultPoint> resultPoints) {
                    // no-op
                }
            });

            dialog.setOnDismissListener(d -> barcodeView.pause());
            dialog.show();

            new Handler(Looper.getMainLooper()).postDelayed(barcodeView::resume, 500);
        } catch (Exception e) {
            Toast.makeText(this, "无法启动扫码，请使用手动输入", Toast.LENGTH_SHORT).show();
        }
    }

    private void handleScannedUrl(String scanned) {
        String url = scanned.trim();
        if (url.startsWith("http://") || url.startsWith("https://")) {
            serverUrlInput.setText(url);
        } else {
            if (url.contains(":") && !url.contains("http")) {
                url = "http://" + url;
            } else if (!url.contains(":")) {
                url = "http://" + url + ":8000/";
            }
            serverUrlInput.setText(url);
        }
        Toast.makeText(this, "地址已填入，请点击保存", Toast.LENGTH_SHORT).show();
    }

    public static String getServerUrl(Context context) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getString(KEY_SERVER_URL, context.getString(R.string.server_url));
    }
}
