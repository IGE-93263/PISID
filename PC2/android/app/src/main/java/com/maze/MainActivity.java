package com.maze;

import android.os.Bundle;
import android.view.MenuItem;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.fragment.app.Fragment;

import com.google.android.material.bottomnavigation.BottomNavigationView;

public class MainActivity extends AppCompatActivity {

    private String host;
    private String database;
    private String username;
    private String password;
    private String tipo;          // "Admin" ou outro — controla privilégios das SPs
    private String idUtilizador;
    private String idGrupo;       // Equipa do utilizador — filtra dados pela simulação corrente da equipa

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        host = getIntent().getStringExtra("host");
        database = getIntent().getStringExtra("database");
        username = getIntent().getStringExtra("username");
        password = getIntent().getStringExtra("password");
        tipo = getIntent().getStringExtra("Tipo");
        idUtilizador = getIntent().getStringExtra("IDUtilizador");
        idGrupo = getIntent().getStringExtra("IDGrupo");

        BottomNavigationView bottomNav = findViewById(R.id.bottom_navigation);
        bottomNav.setOnNavigationItemSelectedListener(navListener);

        // Carrega o fragment inicial
        if (savedInstanceState == null) {
            getSupportFragmentManager().beginTransaction()
                    .replace(R.id.fragment_container, MazeMessagesFragment.newInstance(host, database, username, password, idGrupo))
                    .commit();
        }
    }

    private BottomNavigationView.OnNavigationItemSelectedListener navListener =
            new BottomNavigationView.OnNavigationItemSelectedListener() {
                @Override
                public boolean onNavigationItemSelected(@NonNull MenuItem item) {
                    Fragment selectedFragment = null;

                    int itemId = item.getItemId();
                    if (itemId == R.id.nav_messages) {
                        selectedFragment = MazeMessagesFragment.newInstance(host, database, username, password, idGrupo);
                    } else if (itemId == R.id.nav_room) {
                        selectedFragment = MarsamiRoomFragment.newInstance(host, database, username, password, idGrupo);
                    } else if (itemId == R.id.nav_sound) {
                        selectedFragment = MazeSoundFragment.newInstance(host, database, username, password, idGrupo);
                    } else if (itemId == R.id.nav_temperature) {
                        selectedFragment = MazeTemperatureFragment.newInstance(host, database, username, password, idGrupo);
                    } else if (itemId == R.id.nav_admin) {
                        selectedFragment = AdminFragment.newInstance(host, database, username, password, tipo);
                    }

                    if (selectedFragment != null) {
                        getSupportFragmentManager().beginTransaction()
                                .replace(R.id.fragment_container, selectedFragment)
                                .commit();
                    }
                    return true;
                }
            };
}