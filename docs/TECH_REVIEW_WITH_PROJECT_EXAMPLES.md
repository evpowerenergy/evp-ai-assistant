# ทบทวน Technical Terms + ตัวอย่างจากโปรเจกต์ Crypto Exchange

เอกสารนี้อธิบายศัพท์เทคนิคหลักที่ใช้ในโปรเจกต์ พร้อมยกตัวอย่างโค้ดจริงจากโปรเจกต์ Crypto Exchange (NestJS + TypeORM + PostgreSQL) เพื่อให้จับคู่แนวคิดกับโค้ดได้ชัดเจน

---

## 1. Node.js (JavaScript Runtime Environment)

### มันคืออะไร
Node.js **ไม่ใช่ภาษาโปรแกรม** แต่เป็น **Runtime Environment** ที่สร้างบน **V8 Engine** (ของ Chrome) ทำให้รัน **JavaScript บนฝั่ง Server (Backend)** ได้ ไม่ต้องพึ่งแค่ Browser

### กลไกการทำงานหลัก

| คอนเซปต์ | ความหมาย |
|----------|----------|
| **Single-Threaded** | Process หนึ่งใช้ Thread เดียว ไม่ได้สร้าง Thread ใหม่ทุก Request |
| **Non-blocking I/O** | เมื่อมีงาน I/O (อ่านไฟล์, Query DB) ไม่หยุดรอ แต่ส่งงานไปให้ระบบจัดการ แล้วรับ Request ถัดไปได้ทันที |
| **Asynchronous** | งานที่ใช้เวลาจะทำงานแบบไม่บล็อก แล้วส่งผลกลับผ่าน **Callback / Promise** |
| **Event Loop** | จัดคิวงาน: รับ Event (เช่น DB ตอบกลับ) แล้วเอา Callback ไปรัน ทำให้ Single Thread รองรับ Connection เยอะได้ |

### ทำไมถึงใช้
- **เหมาะ:** I/O Intensive — API ที่ต้องคุย DB บ่อย, เรียก Service ภายนอก (โปรเจกต์เราคือแบบนี้)
- **ไม่เหมาะ:** CPU Intensive — คำนวณเลขหนัก, Image processing (ควรใช้ Worker Thread หรือแยก Service)

### ตัวอย่างในโปรเจกต์ Crypto Exchange

- **จุดที่ Node รัน:** แอป NestJS เริ่มที่ `src/main.ts` — ฟังก์ชัน `bootstrap()` เป็น **async** และ `await app.listen(port)` คือการรอ I/O (รอรับ Connection) โดยไม่บล็อก Thread หลัก

```1:33:src/main.ts
import { NestFactory } from '@nestjs/core';
// ...
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  // ...
  await app.listen(port);
  console.log(`Application is running on: http://localhost:${port}`);
}
bootstrap();
```

- **Async ทั่วทั้งโปรเจกต์:** ทุก Service Method ที่คุย DB ใช้ `async/await` — เช่น `AuthService.register()` รอ `bcrypt.hash()` (CPU-heavy แต่รันใน Worker Pool) และรอ `usersService.create()`, `walletsService.createMany()` ซึ่งเป็น I/O กับ Database

```37:59:src/modules/auth/auth.service.ts
  async register(dto: RegisterDto): Promise<AuthTokens> {
    const existing = await this.usersService.findByEmail(dto.email);
    // ...
    const passwordHash = await bcrypt.hash(dto.password, SALT_ROUNDS);
    const user = await this.usersService.create({ ... });
    const currencies = await this.currenciesService.findAll();
    // ...
    await this.walletsService.createMany(toCreate);
    // ...
  }
```

**สรุป:** โปรเจกต์เป็นแบบ I/O Intensive (DB, JWT, bcrypt) — Node.js รับ Request หลายๆ ตัวพร้อมกัน โดยไม่ต้องสร้าง Thread ใหม่ทุก Request เพราะใช้ Event Loop + Non-blocking I/O

---

## 2. TypeScript (Static Typing for JavaScript)

### มันคืออะไร
TypeScript เป็น **Superset ของ JavaScript** — เพิ่ม **Static Type System** เข้ามา ตัวแปรและฟังก์ชันต้องระบุ (หรือ Infer ได้) ว่าเป็น Type อะไร

### กลไกการทำงานหลัก

- **JavaScript:** Dynamic Type — ตัวแปรเปลี่ยน type กลางทางได้ → Error มักเกิดตอน **Runtime**
- **TypeScript:** ตรวจ Type ตอน **Compile-time** (หรือใน Editor) ถ้าไม่ตรงจะฟ้องก่อนรัน
- **Transpile:** โค้ด TypeScript ถูกแปลงเป็น JavaScript (โดย tsc หรือ esbuild) ก่อนนำไปรันใน Node

### คีย์เวิร์ดที่ต้องรู้

| คำศัพท์ | ความหมาย |
|---------|----------|
| **Interface / Type** | กำหนดรูปร่างของ Object (field อะไร type อะไร) |
| **DTO (Data Transfer Object)** | โครงสร้างข้อมูลที่ Client ส่งมาใน API — ใช้ร่วมกับ class-validator เพื่อ Validate |
| **Generics** | Type ที่รับพารามิเตอร์ เช่น `Promise<Order>`, `Repository<User>` |
| **Strict null** | `string | null` — ต้องคิดกรณี null/undefined ชัดเจน |

### ตัวอย่างในโปรเจกต์ Crypto Exchange

- **Entity = Type ของแถวใน DB:** แต่ละ Entity มี type ชัดเจน เช่น `Order` มี `status: OrderStatus`, `cryptoAmount: string` (decimal เก็บเป็น string ใน TypeORM)

```17:55:src/database/entities/order.entity.ts
@Entity('orders')
export class Order extends BaseEntity {
  @Column({ type: 'uuid', name: 'ad_id' })
  adId!: string;
  // ...
  @Column({ type: 'varchar', length: 20 })
  status!: OrderStatus;
  @Column({ type: 'timestamp', nullable: true, name: 'paid_at' })
  paidAt!: Date | null;
  // ...
}
```

- **DTO + Validation:** ข้อมูลที่ Client ส่งเข้ามา กำหนดเป็น Class พร้อม Decorator จาก **class-validator** — TypeScript บังคับ type, class-validator บังคับกฎ (เช่น email format, ความยาว password)

```1:26:src/modules/auth/dto/register.dto.ts
import { IsEmail, IsString, MinLength, MaxLength, IsOptional } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class RegisterDto {
  @IsEmail()
  @ApiProperty({ example: 'user@example.com' })
  email!: string;

  @IsString()
  @MinLength(8, { message: 'Password must be at least 8 characters' })
  @MaxLength(100)
  password!: string;
  // ...
}
```

- **Return type ชัดเจน:** Service ระบุ return type เป็น `Promise<Order>`, `Promise<AuthTokens>` — เวลาเรียกใช้จาก Controller หรือ Service อื่น จะได้ autocomplete และเช็ค type ได้

**สรุป:** โปรเจกต์ใช้ TypeScript ทั้งหมด — Entity เป็น type ของตาราง, DTO เป็น type ของ Request Body และใช้ร่วมกับ class-validator; การ Transpile ทำตอน build (`npm run build`) ได้เป็น JavaScript ในโฟลเดอร์ `dist/`

---

## 3. NestJS (Progressive Node.js Framework)

### มันคืออะไร
Framework สำหรับสร้าง Backend บน Node.js เน้น **TypeScript**, โครงสร้างแบบ **Module / Controller / Service** และใช้ **Dependency Injection (DI)** ได้แรงบันดาลใจจาก Angular

### กลไกการทำงานหลัก (Architecture)

- **Dependency Injection (DI):** เราไม่เขียน `new OrdersService(...)` เอง แต่ประกาศใน Constructor ว่า "ต้องการ OrdersService" — Nest จะสร้าง Instance (และจัดการ Dependency ย่อยเช่น Repository) ให้แล้ว **ฉีด** เข้ามา
- **ผลที่ได้:** ลดการผูกติด (coupling), ทดสอบด้วย Mock ได้ง่าย, Instance ถูกจัดการเป็น Singleton ภายใน Module

### องค์ประกอบหลัก (Building Blocks)

| องค์ประกอบ | หน้าที่ | ในโปรเจกต์ |
|------------|--------|-------------|
| **Controller (`@Controller`)** | รับ HTTP Request (GET, POST, PATCH, DELETE) และส่ง Response | `AuthController`, `OrdersController`, `WalletsController` ฯลฯ |
| **Provider / Service (`@Injectable`)** | Business Logic, คุยกับ DB ผ่าน Repository | `AuthService`, `OrdersService`, `WalletsService` |
| **Module (`@Module`)** | จัดกลุ่ม Controller, Service, Import  Module อื่น | `AuthModule`, `OrdersModule`, `AppModule` |
| **Guard** | ด่าน Authentication/Authorization (เช่น เช็ค JWT) | `JwtAuthGuard` — ถ้า route ไม่ได้ใส่ `@Public()` ต้องมี Token ถูกต้อง |
| **Pipe** | แปลง/Validate ข้อมูลก่อนเข้า Handler | `ValidationPipe` ใช้ทั้งแอป — ตรวจ DTO ตาม class-validator |

### ตัวอย่างในโปรเจกต์ Crypto Exchange

- **Controller รับ Request → เรียก Service:** Controller ไม่เขียน logic เอง แค่รับ DTO และส่งต่อให้ Service

```12:41:src/modules/auth/auth.controller.ts
@Controller('auth')
@ApiTags('Auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Public()
  @Post('register')
  async register(@Body() dto: RegisterDto) {
    return this.authService.register(dto);
  }
  @Public()
  @Post('login')
  async login(@Body() dto: LoginDto) {
    return this.authService.login(dto);
  }
  // ...
  @UseGuards(JwtAuthGuard)
  @Get('me')
  async me(@CurrentUser() user: User) {
    return this.authService.validateUserById(user.id).then(...);
  }
}
```

- **DI ใน Service:** `OrdersService` ต้องการ Repository และ Service อื่น — ใส่ใน Constructor แล้ว Nest ฉีดให้

```22:33:src/modules/orders/orders.service.ts
@Injectable()
export class OrdersService {
  constructor(
    @InjectRepository(Order)
    private readonly orderRepository: Repository<Order>,
    @InjectRepository(Ad)
    private readonly adRepository: Repository<Ad>,
    private readonly adsService: AdsService,
    private readonly walletsService: WalletsService,
    private readonly transactionsService: TransactionsService,
    private readonly dataSource: DataSource,
  ) {}
```

- **Guard เป็นด่านหน้า:** `JwtAuthGuard` ใช้ทั้งแอปผ่าน `APP_GUARD` — route ใดที่ใส่ `@Public()` จะข้าม Guard นั้น

```1:20:src/common/guards/jwt-auth.guard.ts
@Injectable()
export class JwtAuthGuard extends AuthGuard('jwt') {
  constructor(private reflector: Reflector) {
    super();
  }
  canActivate(context: ExecutionContext) {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) return true;
    return super.canActivate(context);
  }
}
```

- **Module รวมทุกอย่าง:** `OrdersModule` ประกาศใช้ Entity อะไร, Controller อะไร, Provider อะไร, และ Import Module อื่นที่ต้องใช้ (Ads, Wallets, Transactions)

```1:21:src/modules/orders/orders.module.ts
@Module({
  imports: [
    TypeOrmModule.forFeature([Order, Ad]),
    AdsModule,
    WalletsModule,
    TransactionsModule,
  ],
  controllers: [OrdersController],
  providers: [OrdersService],
  exports: [OrdersService],
})
export class OrdersModule {}
```

**สรุป:** โปรเจกต์จัดโครงสร้างตาม NestJS — Controller รับ HTTP, Service ทำ logic + คุย DB, Guard เช็ค JWT, Module เป็นหน่วยรวมและจัดการ DI

---

## 4. TypeORM (Object-Relational Mapper)

### มันคืออะไร
**ORM = Object-Relational Mapper** — จับคู่ระหว่าง **Class (Object)** ในโค้ด กับ **Table** ใน Relational DB (เช่น PostgreSQL)

- แทนที่จะเขียน SQL ดิบ (`SELECT * FROM users WHERE id = $1`) เราจะใช้ Method ของ TypeORM เช่น `userRepository.findOne({ where: { id } })` แล้ว TypeORM แปลงเป็น SQL ให้

### กลไกการทำงานหลัก

- **Entity:** Class หนึ่งตัว = ตารางหนึ่งตาราง
- **Repository:** Object ที่มี method สำหรับ CRUD กับ Entity นั้น (`.find()`, `.findOne()`, `.save()`, `.remove()`)
- **Relations:** กำหนดความสัมพันธ์ระหว่างตาราง (`@OneToMany`, `@ManyToOne`, `@OneToOne`) แล้วโหลดข้อมูลที่เกี่ยวข้องด้วย `relations: ['...']`

### คีย์เวิร์ดที่ต้องรู้

| คำศัพท์ | ความหมาย |
|---------|----------|
| **Entity (`@Entity`)** | Class แทนตาราง — ใช้ `@Column` แทน column |
| **Repository** | API สำหรับ CRUD ของ Entity นั้น — ได้จาก `@InjectRepository(Entity)` |
| **Relations** | `@OneToMany`, `@ManyToOne`, `@OneToOne`, `@JoinColumn` — และการโหลดด้วย `relations: ['ad','buyer']` |
| **Migrations** | Version control ของ Schema (สร้าง/แก้ตาราง) — โปรเจกต์มีโฟลเดอร์ `database/migrations/` |
| **Transaction** | หลาย Query รันเป็นก้อนเดียว — ถ้าใดอันล้ม Rollback ทั้งก้อน (All-or-Nothing) |

### ตัวอย่างในโปรเจกต์ Crypto Exchange

- **Entity = ตาราง:** `Wallet` map กับตาราง `wallets` พร้อมความสัมพันธ์กับ `User`, `Currency`, `Transaction`

```7:34:src/database/entities/wallet.entity.ts
@Entity('wallets')
export class Wallet extends BaseEntity {
  @Column({ type: 'uuid', name: 'user_id' })
  userId!: string;
  @Column({ type: 'decimal', precision: 20, scale: 8, default: 0 })
  balance!: string;
  @Column(..., name: 'locked_balance')
  lockedBalance!: string;

  @ManyToOne(() => User, (u) => u.wallets, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user!: User;

  @ManyToOne(() => Currency, ...)
  @JoinColumn({ name: 'currency_id' })
  currency!: Currency;

  @OneToMany(() => Transaction, (t) => t.wallet)
  transactions!: Transaction[];
}
```

- **Relation สองฝั่ง (Ad ↔ Order):** `Ad` มี `@OneToMany(() => Order, (o) => o.ad)` และ `Order` มี `@ManyToOne(() => Ad, (a) => a.orders)` + `@JoinColumn({ name: 'ad_id' })`

```57:71:src/database/entities/ad.entity.ts
  @ManyToOne(() => User, (u) => u.ads, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user!: User;
  @ManyToOne(() => Currency, ...)
  @JoinColumn({ name: 'crypto_id' })
  crypto!: Currency;
  @ManyToOne(() => Currency, ...)
  @JoinColumn({ name: 'fiat_id' })
  fiat!: Currency;
  @OneToMany(() => Order, (o) => o.ad)
  orders!: Order[];
```

- **ดึงข้อมูลที่สัมพันธ์กัน (เหมือน Eloquent relations):** ใช้ `relations` ใน `findOne` / `find` — โปรเจกต์ดึง Order พร้อม Ad, User (buyer/seller), Transactions

```35:39:src/modules/orders/orders.service.ts
  async findOrderWithDetails(id: string): Promise<Order | null> {
    return this.orderRepository.findOne({
      where: { id },
      relations: ['ad', 'ad.crypto', 'ad.fiat', 'buyer', 'seller', 'transactions'],
    });
  }
```

- **Transaction (All-or-Nothing):** ตอน Seller กด "Release" ต้องอัปเดต wallet 2 ตัว + สร้าง transaction 2 แถว + อัปเดต order — ถ้าขั้นใดขั้นหนึ่งล้ม ต้อง Rollback ทั้งหมด

```135:175:src/modules/orders/orders.service.ts
    await this.dataSource.transaction(async (em) => {
      await this.walletsService.updateBalances(
        sellerWallet.id,
        { lockedBalance: sellerNewLocked },
        em,
      );
      await this.walletsService.updateBalances(
        buyerWallet.id,
        { balance: buyerNewBalance },
        em,
      );
      await this.transactionsService.create(..., em);
      await this.transactionsService.create(..., em);
      order.status = OrderStatus.COMPLETED;
      order.completedAt = new Date();
      await em.getRepository(Order).save(order);
    });
```

**สรุป:** โปรเจกต์ใช้ TypeORM กับ PostgreSQL — Entity = ตาราง, Repository = CRUD, Relations กำหนดใน Entity และโหลดด้วย `relations`, ส่วนงานที่ต้อง atomic ใช้ `dataSource.transaction()` เพื่อความสอดคล้องของข้อมูล

---

## 5. Docker (Containerization Platform)

### มันคืออะไร
แพลตฟอร์มสำหรับสร้างและรัน **Container** — สภาพแวดล้อมรันแอปที่แยกจากเครื่อง host ช่วยแก้ปัญหา "รันที่เครื่องฉันได้ แต่ที่เซิร์ฟเวอร์รันไม่ได้"

### กลไกการทำงานหลัก

- **Image:** Template (Read-only) บอกว่าแอปหรือบริการต้องการอะไร (OS layer, runtime, dependencies)
- **Container:** Instance ที่รันจาก Image — รันได้หลาย Container จาก Image เดียว
- **Docker Compose:** กำหนดการรันหลาย Service (หลาย Container) พร้อมกัน และให้ลิงก์กันได้ (network, env)

### คีย์เวิร์ดที่ต้องรู้

| คำศัพท์ | ความหมาย |
|---------|----------|
| **Image** | พิมพ์เขียวของ Container (อ่านอย่างเดียว) |
| **Container** | Image ที่รันอยู่จริง (มี state ได้) |
| **docker-compose.yml** | ไฟล์กำหนด Services (เช่น postgres, backend) และการเชื่อมต่อ |
| **Volume** | เก็บข้อมูลถาวรนอก Container — ถ้าลบ Container ข้อมูลใน Volume ยังอยู่ |

### ตัวอย่างในโปรเจกต์ Crypto Exchange

โปรเจกต์ใช้ Docker **เฉพาะรัน PostgreSQL** (ไม่ได้ pack Backend เป็น image ในตัวอย่างนี้) — ใช้ `docker-compose.yml` รัน DB หนึ่ง Container

```14:34:docker-compose.yml
services:
  postgres:
    image: postgres:15-alpine
    container_name: crypto_exchange_db
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-crypto}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-crypto_secret}
      POSTGRES_DB: ${POSTGRES_DB:-crypto_exchange}
    ports:
      - "${DB_PORT:-5432}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-crypto} -d ${POSTGRES_DB:-crypto_exchange}"]
      ...
volumes:
  postgres_data:
```

- **Image:** `postgres:15-alpine` — Official PostgreSQL เวอร์ชัน 15 ตัวเล็ก (Alpine)
- **Container:** ชื่อ `crypto_exchange_db` รัน 1 ตัว
- **Volume `postgres_data`:** เก็บข้อมูล DB ในโฮสต์ — รัน `docker-compose down` แล้วขึ้นใหม่ ข้อมูล DB ยังอยู่
- **Port mapping:** `5432:5432` — ให้แอป NestJS บน host เชื่อม `localhost:5432` ไปที่ PostgreSQL ใน Container

Backend (NestJS) รันบนเครื่องเราโดย `npm run start:dev` และต่อ DB ผ่าน `.env` (host, port, user, password, database) ไปที่ Container นี้

**สรุป:** โปรเจกต์ใช้ Docker Compose เพื่อให้ทีมรัน PostgreSQL แบบเดียวกันทุกเครื่อง; Schema สร้างผ่าน TypeORM migrations และข้อมูลทดสอบมาจาก seed

---

## สรุปภาพรวม: โปรเจกต์ Crypto Exchange ประกอบกันอย่างไร

| ชั้น | เทคโนโลยี | หน้าที่ในโปรเจกต์ |
|------|-----------|---------------------|
| Runtime | **Node.js** | รัน JavaScript/TypeScript บนเซิร์ฟเวอร์ แบบ Non-blocking I/O รับ Request หลายๆ ตัวพร้อมกัน |
| ภาษา | **TypeScript** | กำหนด type ให้ Entity, DTO, Service; ใช้กับ class-validator สำหรับ Validate input |
| Framework | **NestJS** | โครงสร้าง Module/Controller/Service, DI, Guard (JWT), Pipe (Validation) |
| ORM / DB | **TypeORM** | Entity = ตาราง, Repository = CRUD, Relations + Transaction สำหรับ logic โอนเงิน/อัปเดตยอด |
| Infrastructure | **Docker (Compose)** | รัน PostgreSQL เป็น Container; Backend รันบน host ต่อ DB ผ่าน .env |

เมื่อมี Request เข้ามา (เช่น `POST /orders`):

1. **Node** รับ HTTP และส่งต่อให้ NestJS
2. **Guard** (ถ้าไม่ใช่ @Public) เช็ค JWT
3. **ValidationPipe** ตรวจ DTO ตาม class-validator (TypeScript + decorator)
4. **Controller** รับ DTO แล้วเรียก **Service**
5. **Service** ใช้ **TypeORM Repository** และ **Transaction** คุยกับ **PostgreSQL** (ที่รันใน Docker)
6. Response ถูกส่งกลับไปที่ Client

ถ้าต้องการเจาะลึกส่วนใดเป็นพิเศษ (เช่น แค่ TypeORM Transaction, แค่ Guard/Passport JWT, หรือ Docker ขั้นถัดไป) บอกได้เลยว่าจะให้โฟกัสหัวข้อไหน
